"""
API Routes — Enterprise Dashboard v2.0

REST endpoints for dashboard data polling, notes, and access requests.
"""

from flask import jsonify, request, abort
from flask_login import login_required, current_user

from app.api import api_bp
from app.extensions import db
from app.models.department import Department
from app.models.access_request import AccessRequest
from app.models.role import PERMISSIONS


# ── Dashboard overview ──────────────────────────────────────────────
@api_bp.route('/dashboard/overview')
@login_required
def dashboard_overview():
    """Company-wide metrics for CEO dashboard polling."""
    from app.dashboard.services import get_overview_metrics, get_company_averages
    depts    = get_overview_metrics()
    averages = get_company_averages()
    import datetime
    return jsonify({
        'departments': depts,
        'averages':    averages,
        'updated_at':  datetime.datetime.utcnow().isoformat(),
    })


# ── Department notes (Director / Developer only) ────────────────────
@api_bp.route('/departments/<int:dept_id>/notes', methods=['POST'])
@login_required
def save_department_notes(dept_id):
    """Save director notes for a group."""
    if not current_user.has_permission(PERMISSIONS['DIRECTOR']):
        abort(403)
    dept = Department.query.get_or_404(dept_id)
    data = request.get_json(force=True) or {}
    dept.director_notes = data.get('notes', '').strip()
    db.session.commit()
    return jsonify({'status': 'ok', 'notes': dept.director_notes})


# ── Set central department (Secretary+) ────────────────────────────
@api_bp.route('/departments/<int:dept_id>/set-central', methods=['POST'])
@login_required
def set_central_department(dept_id):
    """Change which department is the central hub."""
    if not current_user.has_permission(PERMISSIONS['SECRETARY']):
        abort(403)
    Department.query.update({'is_central': False})
    dept = Department.query.get_or_404(dept_id)
    dept.is_central = True
    db.session.commit()
    return jsonify({'status': 'ok', 'central': dept.name})


# ── Pending access-request count (navbar badge) ─────────────────────
@api_bp.route('/access/pending-count')
@login_required
def pending_count():
    """Return pending approval count for the current user's level."""
    count = AccessRequest.query.filter_by(
        status='pending',
        current_approver_level=current_user.permission_level,
    ).count()
    return jsonify({'pending': count})


# ── Health check ────────────────────────────────────────────────────
@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'version': '2.0'})

# ── Main Tasks (الواجبات الرئيسية) ──────────────────────────────────
from app.extensions import csrf

@api_bp.route('/main-tasks', methods=['POST'])
@csrf.exempt
@login_required
def create_main_task():
    """Create a new Main Task for a department."""
    # Require at least SECRETARY level to create tasks (or Developer / Group Admin)
    has_access = (
        current_user.has_permission(PERMISSIONS['SECRETARY']) or 
        current_user.has_permission(PERMISSIONS['GROUP_ADMIN']) or
        current_user.is_developer()
    )
    if not has_access:
        abort(403, description="لا تملك صلاحية إضافة واجب رئيسي")
        
    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'Invalid payload'}), 400
        
    from app.models.main_task import MainTask
    import datetime
    
    try:
        # Parse anticipated end date
        end_date = datetime.datetime.strptime(data['expected_end_date'], '%Y-%m-%d').date()
        
        task = MainTask(
            task_number=data['task_number'],
            description=data['description'],
            completion_pct=int(data.get('completion_pct', 0)),
            expected_end_date=end_date,
            primary_department_id=int(data['primary_dept_id'])
        )
        
        # Link secondary departments if provided (now as JSON text)
        import json
        sec_list = data.get('secondary_dept_list', [])
        task.secondary_departments_list = json.dumps(sec_list, ensure_ascii=False)
            
        db.session.add(task)
        db.session.commit()
        
        return jsonify({'status': 'success', 'task_id': task.id}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
