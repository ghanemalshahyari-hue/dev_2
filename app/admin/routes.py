"""
Admin Blueprint Routes — User, Department, and Role management.

All management actions are DB-driven so no code changes are needed by the client.
Accessible to Deputy (level 80) and above.
"""

from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.admin import admin_bp
from app.models.user import User
from app.models.role import Role, PERMISSIONS
from app.models.department import Department, DepartmentMetrics
from app.models.audit import AuditLog
from app.extensions import db
from app.utils.decorators import require_permission
from app.utils.files import save_base64_image
import uuid


# ─── User Management ─────────────────────────────────────────────────────────

@admin_bp.route('/users')
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def users():
    """List all users."""
    all_users = User.query.order_by(User.full_name).all()
    all_roles = Role.query.order_by(Role.permission_level.desc()).all()
    all_depts = Department.query.order_by(Department.order_index).all()
    return render_template('admin/users.html',
                           all_users=all_users,
                           all_roles=all_roles,
                           all_depts=all_depts,
                           page_title='إدارة المستخدمين')


@admin_bp.route('/users/<user_id>/update', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def update_user(user_id: str):
    """Update a user's role or department."""
    user = User.query.get_or_404(user_id)
    role_id    = request.form.get('role_id', type=int)
    dept_id    = request.form.get('department_id', type=int)
    is_active  = request.form.get('is_active') == 'on'

    old_role = user.role.code if user.role else ''
    if role_id:
        user.role_id = role_id
    if dept_id:
        user.department_id = dept_id
    user.is_active = is_active

    db.session.commit()
    AuditLog.log(
        'admin.user_updated',
        user      = current_user,
        resource_type = 'User',
        resource_id  = user_id,
        details   = f'role changed from {old_role}',
        ip_address = request.remote_addr,
    )
    flash(f'User "{user.full_name}" updated successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/toggle-active', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def toggle_user_active(user_id: str):
    """Activate / deactivate a user account."""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    AuditLog.log(f'admin.user_{status}', user=current_user,
                 resource_type='User', resource_id=user_id,
                 ip_address=request.remote_addr)
    flash(f'User "{user.full_name}" has been {status}.', 'success')
    return redirect(url_for('admin.users'))


# ─── Department (Group) Management ───────────────────────────────────────────

@admin_bp.route('/departments')
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def departments():
    """List and manage all departments/groups."""
    # Exclude the central hub (Strategy) from the management list
    all_depts = Department.query.filter(Department.is_central == False).order_by(Department.order_index).all()
    return render_template('admin/departments.html',
                           all_depts=all_depts,
                           page_title='إدارة المجموعات')


@admin_bp.route('/departments/add', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def add_department():
    """Add a new group/department."""
    last_idx = db.session.query(db.func.max(Department.order_index)).scalar() or 0
    
    # Handle optional logo upload
    logo_file_path = None
    logo_data = request.form.get('logo_base64')
    if logo_data and ',' in logo_data:
        # Save base64 image
        filename = save_base64_image(logo_data, 'img/departments')
        if filename:
            logo_file_path = f'departments/{filename}'

    # Auto-generate code if not provided
    generated_code = f"GRP_{uuid.uuid4().hex[:6].upper()}"

    dept = Department(
        code               = generated_code,
        name               = request.form['name'].strip(),
        concept_number     = request.form.get('concept_number', type=int),
        description        = request.form.get('description', '').strip(),
        responsible_person = request.form.get('responsible_person', '').strip(),
        responsible_name   = request.form.get('responsible_name', '').strip(),
        org_group_name     = request.form.get('org_group_name', '').strip(),
        color              = request.form.get('color', '#4F8EF7'),
        icon               = request.form.get('icon', 'bi-grid-fill'),
        logo_file          = logo_file_path,
        order_index        = last_idx + 1,
        is_active          = True,
    )
    db.session.add(dept)
    db.session.commit()
    AuditLog.log('admin.dept_added', user=current_user,
                 resource_type='Department', resource_id=str(dept.id),
                 ip_address=request.remote_addr)
    flash(f'Group "{dept.name}" created successfully.', 'success')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/departments/<int:dept_id>/update', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def update_department(dept_id: int):
    """Update department details."""
    dept = Department.query.get_or_404(dept_id)
    dept.name               = request.form.get('name', dept.name).strip()
    dept.description        = request.form.get('description', '').strip()
    dept.responsible_person = request.form.get('responsible_person', '').strip()
    dept.responsible_name   = request.form.get('responsible_name', '').strip()
    dept.org_group_name     = request.form.get('org_group_name', '').strip()
    dept.concept_number     = request.form.get('concept_number', type=int)
    dept.color              = request.form.get('color', dept.color)
    dept.icon               = request.form.get('icon', dept.icon)
    
    # Handle logo update
    logo_data = request.form.get('logo_base64')
    if logo_data and ',' in logo_data:
        filename = save_base64_image(logo_data, 'img/departments')
        if filename:
            dept.logo_file = f'departments/{filename}'
            
    db.session.commit()
    AuditLog.log('admin.dept_updated', user=current_user,
                 resource_type='Department', resource_id=str(dept_id),
                 ip_address=request.remote_addr)
    flash(f'Group "{dept.name}" updated.', 'success')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/departments/<int:dept_id>/toggle', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def toggle_department(dept_id: int):
    """Show / hide a department on the CEO dashboard."""
    dept = Department.query.get_or_404(dept_id)
    dept.is_active = not dept.is_active
    db.session.commit()
    status = 'shown' if dept.is_active else 'hidden'
    AuditLog.log(f'admin.dept_{status}', user=current_user,
                 resource_type='Department', resource_id=str(dept_id),
                 ip_address=request.remote_addr)
    flash(f'Group "{dept.name}" is now {status} on the dashboard.', 'success')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['SECRETARY'])
def delete_department(dept_id: int):
    """Permanently remove a department (Secretary+ only)."""
    dept = Department.query.get_or_404(dept_id)
    name = dept.name
    db.session.delete(dept)
    db.session.commit()
    AuditLog.log('admin.dept_deleted', user=current_user,
                 resource_type='Department', resource_id=str(dept_id),
                 details=f'name={name}', ip_address=request.remote_addr)
    flash(f'Group "{name}" permanently deleted.', 'danger')
    return redirect(url_for('admin.departments'))


# ─── Department Metrics Entry ─────────────────────────────────────────────────

@admin_bp.route('/departments/<int:dept_id>/metrics', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['GROUP_ADMIN'])
def update_metrics(dept_id: int):
    """Update competence and completion percentages for a department."""
    dept = Department.query.get_or_404(dept_id)
    # Only the group's own admin (or higher) can update
    if (current_user.role_code == 'GROUP_ADMIN'
            and current_user.department_id != dept_id):
        flash('You can only update metrics for your own group.', 'danger')
        return redirect(url_for('dashboard.group_admin'))

    from datetime import date
    metric = DepartmentMetrics(
        department_id         = dept_id,
        metric_date           = date.today(),
        competence_percentage = float(request.form.get('competence_pct', 0)),
        completion_percentage = float(request.form.get('completion_pct', 0)),
        notes                 = request.form.get('notes', '').strip(),
        updated_by_id         = current_user.id,
    )
    db.session.add(metric)
    db.session.commit()
    AuditLog.log('admin.metrics_updated', user=current_user,
                 resource_type='Department', resource_id=str(dept_id),
                 ip_address=request.remote_addr)
    flash(f'Metrics for "{dept.name}" updated.', 'success')
    return redirect(url_for('dashboard.group_admin'))


# ─── Role Management ──────────────────────────────────────────────────────────

@admin_bp.route('/roles')
@login_required
@require_permission(PERMISSIONS['SECRETARY'])
def roles():
    """Deprecated: Redirect to users page (consolidated view)."""
    return redirect(url_for('admin.users'))


@admin_bp.route('/roles/<int:role_id>/update', methods=['POST'])
@login_required
@require_permission(PERMISSIONS['SECRETARY'])
def update_role(role_id: int):
    """Update a role's display name or description (level is protected for system roles)."""
    role = Role.query.get_or_404(role_id)
    role.name        = request.form.get('name', role.name).strip()
    role.name_ar     = request.form.get('name_ar', role.name_ar).strip()
    role.description = request.form.get('description', role.description).strip()
    # Only DEVELOPER can change permission levels
    if current_user.role_code == 'DEVELOPER' and not role.is_system:
        new_level = request.form.get('permission_level', type=int)
        if new_level is not None:
            role.permission_level = new_level
    db.session.commit()
    AuditLog.log('admin.role_updated', user=current_user,
                 resource_type='Role', resource_id=str(role_id),
                 ip_address=request.remote_addr)
    flash(f'Role "{role.name}" updated.', 'success')
    return redirect(url_for('admin.users'))


# ─── Audit Log ────────────────────────────────────────────────────────────────

@admin_bp.route('/audit-log')
@login_required
@require_permission(PERMISSIONS['SECRETARY'])
def audit_log():
    """View system audit trail."""
    page   = request.args.get('page', 1, type=int)
    action = request.args.get('action', '')
    query  = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if action:
        query = query.filter(AuditLog.action.contains(action))
    logs = query.paginate(page=page, per_page=50, error_out=False)
    return render_template('admin/audit_log.html',
                           logs=logs,
                           action_filter=action,
                           page_title='سجل التدقيق')
