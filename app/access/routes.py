"""
Access Request Blueprint — Multi-level approval workflow.

Flow: User submits → Group Admin → Deputy → Secretary → Director
Each level can Approve (pass up) or Reject (with mandatory reason).
"""

from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.access import access_bp
from app.models.access_request import AccessRequest, AccessApproval
from app.models.role import Role, PERMISSIONS
from app.models.department import Department
from app.models.audit import AuditLog
from app.extensions import db

# Level progression: Group Admin → Deputy → Secretary → Director → Done
_APPROVAL_CHAIN = [
    PERMISSIONS['GROUP_ADMIN'],   # 60
    PERMISSIONS['DEPUTY'],        # 80
    PERMISSIONS['SECRETARY'],     # 90
    PERMISSIONS['DIRECTOR'],      # 100
]


def _next_level(current: int):
    """Return the next approval level, or None if this was the final level."""
    try:
        idx = _APPROVAL_CHAIN.index(current)
        return _APPROVAL_CHAIN[idx + 1] if idx + 1 < len(_APPROVAL_CHAIN) else None
    except ValueError:
        return None


# ─── User: submit request ─────────────────────────────────────────────────────

@access_bp.route('/request', methods=['GET', 'POST'])
@login_required
def new_request():
    """User submits a new access request."""
    roles = Role.query.order_by(Role.permission_level).all()
    depts = Department.active_ordered()

    if request.method == 'POST':
        role_code   = request.form.get('role_code', '').strip()
        dept_id     = request.form.get('department_id', type=int)
        justify     = request.form.get('justification', '').strip()

        if not role_code or not justify:
            flash('Please fill in all required fields.', 'danger')
            return render_template('access/request.html', roles=roles, depts=depts,
                                   page_title='طلب صلاحية')

        req = AccessRequest(
            requester_id            = current_user.id,
            requested_role_code     = role_code,
            requested_department_id = dept_id or None,
            justification           = justify,
            current_approver_level  = PERMISSIONS['GROUP_ADMIN'],
        )
        db.session.add(req)
        db.session.commit()
        AuditLog.log('access.request_submitted', user=current_user,
                     resource_type='AccessRequest', resource_id=req.id,
                     ip_address=request.remote_addr)
        flash('Your access request has been submitted and is awaiting approval.', 'success')
        return redirect(url_for('dashboard.user_view'))

    return render_template('access/request.html', roles=roles, depts=depts,
                           page_title='طلب صلاحية')


# ─── Approver: pending queue ──────────────────────────────────────────────────

@access_bp.route('/pending')
@login_required
def pending():
    """Show access requests waiting for approval at the current user's level."""
    level = current_user.permission_level
    requests_at_level = AccessRequest.query.filter_by(
        status='pending',
        current_approver_level=level,
    ).order_by(AccessRequest.created_at).all()

    return render_template('access/pending.html',
                           requests=requests_at_level,
                           page_title='طلبات الصلاحيات المعلقة')


# ─── Approve ──────────────────────────────────────────────────────────────────

@access_bp.route('/<request_id>/approve', methods=['POST'])
@login_required
def approve(request_id: str):
    """Approve a request at the current user's level."""
    req = AccessRequest.query.get_or_404(request_id)

    if req.current_approver_level != current_user.permission_level:
        flash('This request is not awaiting your approval.', 'danger')
        return redirect(url_for('access.pending'))

    next_level = _next_level(req.current_approver_level)
    req.approve_at_level(current_user, next_level)

    AuditLog.log('access.approved', user=current_user,
                 resource_type='AccessRequest', resource_id=request_id,
                 details=f'next_level={next_level}',
                 ip_address=request.remote_addr)

    if next_level is None:
        # Fully approved — apply the role change
        _apply_approved_request(req)
        flash('Request fully approved and role has been applied.', 'success')
    else:
        flash('Request approved and passed to the next level.', 'success')

    return redirect(url_for('access.pending'))


# ─── Reject ───────────────────────────────────────────────────────────────────

@access_bp.route('/<request_id>/reject', methods=['POST'])
@login_required
def reject(request_id: str):
    """Reject a request — reason is mandatory."""
    req = AccessRequest.query.get_or_404(request_id)

    if req.current_approver_level != current_user.permission_level:
        flash('This request is not awaiting your approval.', 'danger')
        return redirect(url_for('access.pending'))

    reason = request.form.get('rejection_reason', '').strip()
    if not reason:
        flash('A rejection reason is required.', 'danger')
        return redirect(url_for('access.pending'))

    req.reject_at_level(current_user, reason)
    AuditLog.log('access.rejected', user=current_user,
                 resource_type='AccessRequest', resource_id=request_id,
                 details=f'reason={reason[:100]}',
                 ip_address=request.remote_addr)
    flash('Request has been rejected and the requester will be notified.', 'success')
    return redirect(url_for('access.pending'))


# ─── My requests ─────────────────────────────────────────────────────────────

@access_bp.route('/my-requests')
@login_required
def my_requests():
    """Show all access requests submitted by the current user."""
    reqs = AccessRequest.query.filter_by(
        requester_id=current_user.id
    ).order_by(AccessRequest.created_at.desc()).all()
    return render_template('access/my_requests.html',
                           requests=reqs,
                           page_title='طلباتي')


# ─── Helper ───────────────────────────────────────────────────────────────────

def _apply_approved_request(req: AccessRequest) -> None:
    """Apply the approved role/department change to the user."""
    from app.models.user import User
    user = User.query.get(req.requester_id)
    if not user:
        return
    role = Role.get_by_code(req.requested_role_code)
    if role:
        user.role_id = role.id
    if req.requested_department_id:
        user.department_id = req.requested_department_id
    db.session.commit()
