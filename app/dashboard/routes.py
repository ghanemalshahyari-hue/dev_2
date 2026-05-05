"""
Dashboard Routes — Role-based redirect after login.

Director  → CEO circular dashboard
Secretary → Planning & coordination view
Deputy    → Decisions & approvals view
GroupAdmin → Group data entry view
User      → Personal view + access request
Developer → Full dev panel (all views available)
"""

from flask import render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from app.dashboard import dashboard_bp
from app.dashboard.services import get_overview_metrics, get_company_averages
from app.models.department import Department
from app.models.access_request import AccessRequest
from app.utils.decorators import require_permission
from app.models.role import PERMISSIONS


@dashboard_bp.route('/')
@login_required
def index():
    """Route all users to their role-specific dashboard."""
    mapping = {
        'DEVELOPER':   'dashboard.developer',
        'DIRECTOR':    'dashboard.director',
        'SECRETARY':   'dashboard.secretary',
        'DEPUTY':      'dashboard.deputy',
        'GROUP_ADMIN': 'dashboard.group_admin',
        'USER':        'dashboard.user_view',
    }
    target = mapping.get(current_user.role_code, 'dashboard.user_view')
    return redirect(url_for(target))


# ─── Director / CEO ───────────────────────────────────────────────────────────

@dashboard_bp.route('/director')
@login_required
@require_permission(PERMISSIONS['DIRECTOR'])
def director():
    """CEO circular dashboard — 7 department cards with competence & completion %."""
    departments = get_overview_metrics()
    averages    = get_company_averages()
    return render_template(
        'dashboard/director.html',
        departments=departments,
        averages=averages,
        page_title='لوحة المدير',
    )


# ─── Secretary ────────────────────────────────────────────────────────────────

@dashboard_bp.route('/secretary')
@login_required
@require_permission(PERMISSIONS['SECRETARY'])
def secretary():
    """Secretary planning & coordination view."""
    departments = get_overview_metrics()
    averages    = get_company_averages()
    pending_requests = AccessRequest.query.filter_by(
        status='pending',
        current_approver_level=PERMISSIONS['SECRETARY'],
    ).count()
    return render_template(
        'dashboard/secretary.html',
        departments=departments,
        averages=averages,
        pending_requests=pending_requests,
        page_title='لوحة السكرتير',
    )


# ─── Deputy ───────────────────────────────────────────────────────────────────

@dashboard_bp.route('/deputy')
@login_required
@require_permission(PERMISSIONS['DEPUTY'])
def deputy():
    """Deputy decisions & approvals view."""
    departments = get_overview_metrics()
    averages    = get_company_averages()
    pending_requests = AccessRequest.query.filter_by(
        status='pending',
        current_approver_level=PERMISSIONS['DEPUTY'],
    ).count()
    return render_template(
        'dashboard/deputy.html',
        departments=departments,
        averages=averages,
        pending_requests=pending_requests,
        page_title='لوحة نائب المدير',
    )


# ─── Group Admin ──────────────────────────────────────────────────────────────

@dashboard_bp.route('/group-admin')
@login_required
@require_permission(PERMISSIONS['GROUP_ADMIN'])
def group_admin():
    """Group administrator data entry & metrics view."""
    dept = current_user.department
    if not dept and not current_user.is_developer():
        abort(403)

    # Devs see all depts
    if current_user.is_developer():
        departments = Department.active_ordered()
    else:
        departments = [dept] if dept else []

    pending_requests = AccessRequest.query.filter_by(
        status='pending',
        current_approver_level=PERMISSIONS['GROUP_ADMIN'],
    ).count()

    return render_template(
        'dashboard/group_admin.html',
        departments=departments,
        pending_requests=pending_requests,
        page_title='لوحة مدير المجموعة',
    )


# ─── User ─────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/user')
@login_required
def user_view():
    """Regular user personal dashboard and access request form."""
    my_requests = AccessRequest.query.filter_by(
        requester_id=current_user.id
    ).order_by(AccessRequest.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/user.html',
        my_requests=my_requests,
        page_title='لوحة المستخدم',
    )


# ─── Developer ────────────────────────────────────────────────────────────────

@dashboard_bp.route('/developer')
@login_required
@require_permission(PERMISSIONS['DEVELOPER'])
def developer():
    """Developer full-access panel — includes all views and system info."""
    departments      = get_overview_metrics()
    averages         = get_company_averages()
    all_requests     = AccessRequest.query.order_by(
        AccessRequest.created_at.desc()
    ).limit(10).all()
    from app.models.user import User
    from app.models.role import Role
    total_users = User.query.count()
    total_depts = Department.query.count()
    return render_template(
        'dashboard/developer.html',
        departments=departments,
        averages=averages,
        all_requests=all_requests,
        total_users=total_users,
        total_depts=total_depts,
        page_title='لوحة المطور',
    )


# ─── Group Details & Main Tasks ───────────────────────────────────────────────

@dashboard_bp.route('/department/<int:dept_id>')
@login_required
def department_detail(dept_id):
    """View details for a specific department and its main tasks."""
    from app.models.main_task import MainTask
    dept = Department.query.get_or_404(dept_id)
    
    # All main tasks where this department is primary
    tasks = MainTask.query.filter_by(primary_department_id=dept_id).order_by(MainTask.task_number).all()
    
    # Also fetch all other active departments to populate the "add secondary department" select
    all_depts = Department.active_ordered()
    
    return render_template(
        'dashboard/department_detail.html',
        dept=dept,
        tasks=tasks,
        all_depts=all_depts,
        page_title=f'تفاصيل: {dept.name}'
    )
