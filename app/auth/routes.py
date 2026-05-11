"""
Auth Blueprint Routes — Login / Logout

Security features:
- CSRF protection on login form
- Rate limiting (5 attempts → 15 min lockout)
- Audit logging on every attempt
- Session regeneration post-login
"""

from __future__ import annotations

from flask import (
    render_template, redirect, url_for,
    flash, request, session, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.auth.ldap_client import get_ldap_client
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.audit import AuditLog


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """LDAP login — redirects authenticated users to their role dashboard."""
    if current_user.is_authenticated:
        return redirect(_role_dashboard())

    # Check LDAP connectivity for the status indicator
    ldap_ok = True
    try:
        client  = get_ldap_client()
        ldap_ok, _ = client.test_connection()
    except Exception:
        ldap_ok = False

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        password = form.password.data

        # ── Pre-auth: check if user exists and is locked out ──
        db_user = User.get_by_username(username)

        if db_user and db_user.is_locked_out():
            flash(
                'Account is temporarily locked due to too many failed attempts. '
                'Please try again in 15 minutes.',
                'danger'
            )
            AuditLog.log(
                'auth.lockout_attempt', user=db_user,
                ip_address=request.remote_addr,
            )
            return render_template('auth/login.html', form=form, ldap_ok=ldap_ok)

        # ── Attempt LDAP (or simulation) authentication ──
        client            = get_ldap_client()
        success, ldap_user, error = client.authenticate(username, password)

        if not success:
            if db_user:
                db_user.record_failed_login(
                    max_attempts     = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5),
                    lockout_minutes  = current_app.config.get('LOCKOUT_DURATION_MINUTES', 15),
                )
            AuditLog.log(
                'auth.login_failed',
                user      = db_user,
                details   = error,
                ip_address= request.remote_addr,
                user_agent= request.user_agent.string[:255],
            )
            flash(f'Login failed: {error}', 'danger')
            return render_template('auth/login.html', form=form, ldap_ok=ldap_ok)

        # ── Success: find or create user record in DB ──
        if db_user is None:
            db_user = _provision_user(ldap_user)

        if not db_user.is_active:
            flash('Your account has been deactivated. Contact the administrator.', 'danger')
            return render_template('auth/login.html', form=form, ldap_ok=ldap_ok)

        # ── Regen session (prevent fixation) ──
        session.clear()

        login_user(db_user, remember=form.remember_me.data)
        db_user.record_successful_login()

        AuditLog.log(
            'auth.login_success',
            user       = db_user,
            ip_address = request.remote_addr,
            user_agent = request.user_agent.string[:255],
        )

        # ── Redirect to intended page or role dashboard ──
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):   # relative only, no open redirect
            return redirect(next_page)
        return redirect(_role_dashboard())

    return render_template('auth/login.html', form=form, ldap_ok=ldap_ok)


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logout: clear session and audit log."""
    AuditLog.log(
        'auth.logout',
        user       = current_user,
        ip_address = request.remote_addr,
    )
    logout_user()
    session.clear()
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _role_dashboard() -> str:
    """Return the shared landing screen after login."""
    return url_for('dashboard.index')


def _provision_user(ldap_user) -> User:
    """
    Create a new User record from LDAP data.
    Role is determined by LDAP group membership (or 'USER' as default).
    """
    from app.auth.ldap_client import _SIMULATION_USERS

    # Map role: in sim mode the LDAP user carries role_code via groups string
    role_code = 'USER'
    for g in ldap_user.groups:
        for code in ('DEVELOPER', 'DIRECTOR', 'SECRETARY', 'DEPUTY', 'GROUP_ADMIN'):
            if code in g.upper():
                role_code = code
                break

    role = Role.get_by_code(role_code) or Role.get_by_code('USER')

    # Map department
    dept = None
    if ldap_user.department:
        dept = Department.query.filter_by(code=ldap_user.department).first() \
            or Department.query.first()

    user = User(
        username     = ldap_user.username,
        email        = ldap_user.email,
        full_name    = ldap_user.full_name,
        ldap_dn      = ldap_user.dn,
        is_ldap_user = True,
        role_id      = role.id if role else None,
        department_id = dept.id if dept else None,
    )
    db.session.add(user)
    db.session.commit()
    return user
