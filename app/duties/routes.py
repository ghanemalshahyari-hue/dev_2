"""
Duties Blueprint - مسارات الواجبات والمشاريع

يوفر:
- عرض الواجبات بشكل هرمي
- عرض Gantt Chart
- عرض Kanban
- إدارة الواجبات والمشاريع والأنشطة
"""

from datetime import date, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Department, User,
    Entity, Duty, DutyStatus,
    Objective, Project, Activity, ActivityStatus,
    ActivityOutput, Deliverable,
    get_duty_full_hierarchy, get_department_timeline
)


bp = Blueprint('duties', __name__, url_prefix='/duties')


@bp.route('/')
@login_required
def index():
    """عرض جميع الواجبات"""
    
    departments = Department.get_all_active()
    
    # جلب الواجبات حسب صلاحيات المستخدم
    if current_user.permission_level >= 80:  # نائب المدير فأعلى
        duties = Duty.query.filter_by(is_active=True).order_by(Duty.department_id, Duty.order_index).all()
    elif current_user.department_id:
        duties = Duty.query.filter_by(
            department_id=current_user.department_id,
            is_active=True
        ).order_by(Duty.order_index).all()
    else:
        duties = []
    
    # حساب الإحصائيات
    total_objectives = sum(d.objectives.filter_by(is_active=True).count() for d in duties)
    total_projects = 0
    total_activities = 0
    
    for duty in duties:
        for obj in duty.objectives.filter_by(is_active=True).all():
            total_projects += obj.projects.filter_by(is_active=True).count()
            for proj in obj.projects.filter_by(is_active=True).all():
                total_activities += proj.activities.filter_by(is_active=True).count()
    
    # بيانات الجدول الزمني
    current_year = date.today().year
    timeline_start = date(current_year, 1, 1)
    timeline_end = date(current_year + 5, 12, 31)
    timeline_total_days = (timeline_end - timeline_start).days
    
    timeline_data = []
    for duty in duties:
        for obj in duty.objectives.filter_by(is_active=True).all():
            for proj in obj.projects.filter_by(is_active=True).all():
                for act in proj.activities.filter_by(is_active=True).all():
                    if act.start_date and act.end_date:
                        timeline_data.append({
                            'duty': duty,
                            'objective': obj,
                            'project': proj,
                            'activity': act,
                            'start': act.start_date,
                            'end': act.end_date,
                            'completion': act.completion_percentage
                        })
    
    timeline_data.sort(key=lambda x: x['start'])
    
    # تصنيف الأنشطة حسب الحالة للـ Kanban
    all_activities = Activity.query.join(Project).join(Objective).join(Duty).filter(
        Duty.is_active == True,
        Activity.is_active == True
    ).all()
    
    activities_by_status = {
        'not_started': [a for a in all_activities if a.status == 'not_started'],
        'in_progress': [a for a in all_activities if a.status == 'in_progress'],
        'delayed': [a for a in all_activities if a.status == 'delayed'],
        'completed': [a for a in all_activities if a.status == 'completed']
    }
    
    return render_template('duties/index.html',
        departments=departments,
        department=None,
        duties=duties,
        total_objectives=total_objectives,
        total_projects=total_projects,
        total_activities=total_activities,
        current_year=current_year,
        timeline_data=timeline_data,
        timeline_start=timeline_start,
        timeline_total_days=timeline_total_days,
        activities_by_status=activities_by_status
    )


@bp.route('/department/<int:dept_id>')
@login_required
def by_department(dept_id):
    """عرض واجبات مجموعة معينة"""
    
    department = Department.query.get_or_404(dept_id)
    departments = Department.get_all_active()
    
    # التحقق من الصلاحيات
    if current_user.permission_level < 80 and current_user.department_id != dept_id:
        flash('ليس لديك صلاحية الوصول لهذه المجموعة', 'danger')
        return redirect(url_for('duties.index'))
    
    duties = Duty.query.filter_by(
        department_id=dept_id,
        is_active=True
    ).order_by(Duty.order_index).all()
    
    # حساب الإحصائيات
    total_objectives = sum(d.objectives.filter_by(is_active=True).count() for d in duties)
    total_projects = 0
    total_activities = 0
    
    for duty in duties:
        for obj in duty.objectives.filter_by(is_active=True).all():
            total_projects += obj.projects.filter_by(is_active=True).count()
            for proj in obj.projects.filter_by(is_active=True).all():
                total_activities += proj.activities.filter_by(is_active=True).count()
    
    # بيانات الجدول الزمني
    current_year = date.today().year
    timeline_start = date(current_year, 1, 1)
    timeline_end = date(current_year + 5, 12, 31)
    timeline_total_days = (timeline_end - timeline_start).days
    
    timeline_data = get_department_timeline(dept_id, current_year, current_year + 5)
    
    # تصنيف الأنشطة للـ Kanban
    all_activities = Activity.query.join(Project).join(Objective).join(Duty).filter(
        Duty.department_id == dept_id,
        Duty.is_active == True,
        Activity.is_active == True
    ).all()
    
    activities_by_status = {
        'not_started': [a for a in all_activities if a.status == 'not_started'],
        'in_progress': [a for a in all_activities if a.status == 'in_progress'],
        'delayed': [a for a in all_activities if a.status == 'delayed'],
        'completed': [a for a in all_activities if a.status == 'completed']
    }
    
    return render_template('duties/index.html',
        departments=departments,
        department=department,
        duties=duties,
        total_objectives=total_objectives,
        total_projects=total_projects,
        total_activities=total_activities,
        current_year=current_year,
        timeline_data=timeline_data,
        timeline_start=timeline_start,
        timeline_total_days=timeline_total_days,
        activities_by_status=activities_by_status
    )


@bp.route('/duty/<int:duty_id>')
@login_required
def duty_detail(duty_id):
    """عرض تفاصيل واجب"""
    
    duty = Duty.query.get_or_404(duty_id)
    
    # التحقق من الصلاحيات
    if current_user.permission_level < 80 and current_user.department_id != duty.department_id:
        flash('ليس لديك صلاحية الوصول لهذا الواجب', 'danger')
        return redirect(url_for('duties.index'))
    
    hierarchy = get_duty_full_hierarchy(duty_id)
    
    return render_template('duties/detail.html',
        duty=duty,
        hierarchy=hierarchy
    )


# ========== API Endpoints ==========

@bp.route('/api/activity/<int:activity_id>/update', methods=['POST'])
@login_required
def update_activity(activity_id):
    """تحديث نسبة إنجاز نشاط"""
    
    activity = Activity.query.get_or_404(activity_id)
    
    # التحقق من الصلاحيات
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    if 'completion_percentage' in data:
        activity.completion_percentage = float(data['completion_percentage'])
        activity.data_filled = True
        activity.update_status()
    
    if 'notes' in data:
        activity.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'completion': activity.completion_percentage,
        'status': activity.status
    })


@bp.route('/api/stats')
@login_required
def get_stats():
    """جلب إحصائيات الواجبات"""
    
    if current_user.permission_level >= 80:
        duties_count = Duty.query.filter_by(is_active=True).count()
        objectives_count = Objective.query.filter_by(is_active=True).count()
        projects_count = Project.query.filter_by(is_active=True).count()
        activities_count = Activity.query.filter_by(is_active=True).count()
    elif current_user.department_id:
        duties_count = Duty.query.filter_by(
            department_id=current_user.department_id,
            is_active=True
        ).count()
        
        duties = Duty.query.filter_by(
            department_id=current_user.department_id,
            is_active=True
        ).all()
        
        objectives_count = sum(d.objectives.filter_by(is_active=True).count() for d in duties)
        projects_count = 0
        activities_count = 0
        
        for duty in duties:
            for obj in duty.objectives.filter_by(is_active=True).all():
                projects_count += obj.projects.filter_by(is_active=True).count()
                for proj in obj.projects.filter_by(is_active=True).all():
                    activities_count += proj.activities.filter_by(is_active=True).count()
    else:
        duties_count = 0
        objectives_count = 0
        projects_count = 0
        activities_count = 0
    
    return jsonify({
        'duties': duties_count,
        'objectives': objectives_count,
        'projects': projects_count,
        'activities': activities_count
    })


# ========== إضافة العناصر ==========

@bp.route('/api/entity/add', methods=['POST'])
@login_required
def add_entity():
    """إضافة جهة جديدة"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    dept_id = data.get('department_id') or current_user.department_id
    if not dept_id:
        return jsonify({'success': False, 'message': 'يجب تحديد المجموعة'}), 400
    
    # التحقق من عدم تكرار الكود
    existing = Entity.query.filter_by(department_id=dept_id, code=data.get('code')).first()
    if existing:
        return jsonify({'success': False, 'message': 'رمز الجهة موجود مسبقاً'}), 400
    
    entity = Entity(
        department_id=dept_id,
        code=data.get('code'),
        name=data.get('name'),
        description=data.get('description', ''),
        manager_id=data.get('manager_id'),
        order_index=Entity.query.filter_by(department_id=dept_id).count()
    )
    
    db.session.add(entity)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'entity': {
            'id': entity.id,
            'code': entity.code,
            'name': entity.name
        }
    })


@bp.route('/api/duty/add', methods=['POST'])
@login_required
def add_duty():
    """إضافة واجب جديد"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    dept_id = data.get('department_id') or current_user.department_id
    if not dept_id:
        return jsonify({'success': False, 'message': 'يجب تحديد المجموعة'}), 400
    
    # التحقق من عدم تكرار رقم الواجب
    existing = Duty.query.filter_by(department_id=dept_id, duty_number=data.get('duty_number')).first()
    if existing:
        return jsonify({'success': False, 'message': 'رقم الواجب موجود مسبقاً'}), 400
    
    from datetime import date
    current_year = date.today().year
    
    duty = Duty(
        department_id=dept_id,
        entity_id=data.get('entity_id'),
        duty_number=data.get('duty_number'),
        title=data.get('title'),
        description=data.get('description', ''),
        priority=int(data.get('priority', 1)),
        status=data.get('status', 'planning'),
        start_year=int(data.get('start_year', current_year)),
        end_year=int(data.get('end_year', current_year + 5)),
        completion_method=data.get('completion_method', 'auto_activities'),
        created_by=current_user.id,
        order_index=Duty.query.filter_by(department_id=dept_id).count()
    )
    
    db.session.add(duty)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'duty': {
            'id': duty.id,
            'duty_number': duty.duty_number,
            'title': duty.title
        }
    })


@bp.route('/api/objective/add', methods=['POST'])
@login_required
def add_objective():
    """إضافة هدف جديد"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    duty_id = data.get('duty_id')
    if not duty_id:
        return jsonify({'success': False, 'message': 'يجب تحديد الواجب'}), 400
    
    duty = Duty.query.get(duty_id)
    if not duty:
        return jsonify({'success': False, 'message': 'الواجب غير موجود'}), 404
    
    # التحقق من الصلاحيات
    if current_user.permission_level < 80 and current_user.department_id != duty.department_id:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية على هذا الواجب'}), 403
    
    objective = Objective(
        duty_id=duty_id,
        objective_number=data.get('objective_number'),
        title=data.get('title'),
        description=data.get('description', ''),
        target_indicator=data.get('target_indicator', ''),
        target_value=float(data.get('target_value', 0)) if data.get('target_value') else None,
        start_date=date.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=date.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        order_index=Objective.query.filter_by(duty_id=duty_id).count()
    )
    
    db.session.add(objective)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'objective': {
            'id': objective.id,
            'objective_number': objective.objective_number,
            'title': objective.title
        }
    })


@bp.route('/api/project/add', methods=['POST'])
@login_required
def add_project():
    """إضافة مشروع جديد"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    objective_id = data.get('objective_id')
    if not objective_id:
        return jsonify({'success': False, 'message': 'يجب تحديد الهدف'}), 400
    
    objective = Objective.query.get(objective_id)
    if not objective:
        return jsonify({'success': False, 'message': 'الهدف غير موجود'}), 404
    
    # التحقق من الصلاحيات
    duty = objective.duty
    if current_user.permission_level < 80 and current_user.department_id != duty.department_id:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    project = Project(
        objective_id=objective_id,
        project_number=data.get('project_number'),
        title=data.get('title'),
        description=data.get('description', ''),
        start_date=date.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=date.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        budget=float(data.get('budget')) if data.get('budget') else None,
        manager_id=data.get('manager_id'),
        completion_method=data.get('completion_method', 'auto_activities'),
        order_index=Project.query.filter_by(objective_id=objective_id).count()
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'project': {
            'id': project.id,
            'project_number': project.project_number,
            'title': project.title
        }
    })


@bp.route('/api/activity/add', methods=['POST'])
@login_required
def add_activity():
    """إضافة نشاط جديد"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    data = request.get_json()
    
    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'success': False, 'message': 'يجب تحديد المشروع'}), 400
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': 'المشروع غير موجود'}), 404
    
    # التحقق من الصلاحيات
    duty = project.objective.duty
    if current_user.permission_level < 80 and current_user.department_id != duty.department_id:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    activity = Activity(
        project_id=project_id,
        activity_number=data.get('activity_number'),
        title=data.get('title'),
        description=data.get('description', ''),
        start_date=date.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=date.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        assignee_id=data.get('assignee_id'),
        status=data.get('status', 'not_started'),
        order_index=Activity.query.filter_by(project_id=project_id).count()
    )
    
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'activity': {
            'id': activity.id,
            'activity_number': activity.activity_number,
            'title': activity.title
        }
    })


# ========== جلب البيانات للقوائم المنسدلة ==========

@bp.route('/api/entities/<int:dept_id>')
@login_required
def get_entities(dept_id):
    """جلب جهات مجموعة"""
    entities = Entity.query.filter_by(department_id=dept_id, is_active=True).order_by(Entity.order_index).all()
    return jsonify([{
        'id': e.id,
        'code': e.code,
        'name': e.name
    } for e in entities])


@bp.route('/api/duties/<int:dept_id>')
@login_required
def get_duties_by_dept(dept_id):
    """جلب واجبات مجموعة"""
    duties = Duty.query.filter_by(department_id=dept_id, is_active=True).order_by(Duty.order_index).all()
    return jsonify([{
        'id': d.id,
        'duty_number': d.duty_number,
        'title': d.title
    } for d in duties])


@bp.route('/api/objectives/<int:duty_id>')
@login_required
def get_objectives_by_duty(duty_id):
    """جلب أهداف واجب"""
    objectives = Objective.query.filter_by(duty_id=duty_id, is_active=True).order_by(Objective.order_index).all()
    return jsonify([{
        'id': o.id,
        'objective_number': o.objective_number,
        'title': o.title
    } for o in objectives])


@bp.route('/api/projects/<int:objective_id>')
@login_required
def get_projects_by_objective(objective_id):
    """جلب مشاريع هدف"""
    projects = Project.query.filter_by(objective_id=objective_id, is_active=True).order_by(Project.order_index).all()
    return jsonify([{
        'id': p.id,
        'project_number': p.project_number,
        'title': p.title
    } for p in projects])


# ========== حذف العناصر ==========

@bp.route('/api/duty/<int:duty_id>/delete', methods=['POST'])
@login_required
def delete_duty(duty_id):
    """حذف واجب (تعطيل)"""
    if current_user.permission_level < 80:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    duty = Duty.query.get_or_404(duty_id)
    duty.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/objective/<int:objective_id>/delete', methods=['POST'])
@login_required
def delete_objective(objective_id):
    """حذف هدف (تعطيل)"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    objective = Objective.query.get_or_404(objective_id)
    objective.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """حذف مشروع (تعطيل)"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    project = Project.query.get_or_404(project_id)
    project.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/activity/<int:activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(activity_id):
    """حذف نشاط (تعطيل)"""
    if current_user.permission_level < 60:
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية'}), 403
    
    activity = Activity.query.get_or_404(activity_id)
    activity.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})
