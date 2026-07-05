"""
Dashboard Routes — Role-based redirect after login.

Director  → CEO circular dashboard
Secretary → Planning & coordination view
Deputy    → Decisions & approvals view
GroupAdmin → Group data entry view
User      → Personal view + access request
Developer → Full dev panel (all views available)
"""

from datetime import datetime

from flask import render_template, url_for, abort, request, redirect, flash, jsonify
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
    """Main landing screen after login."""
    departments = get_overview_metrics()
    averages = get_company_averages()
    return render_template(
        'dashboard/home.html',
        departments=departments,
        averages=averages,
        page_title='الرئيسية',
    )


@dashboard_bp.route('/org-structure')
@login_required
def org_structure():
    """Organizational structure — tree view driven by Department + MainTask data."""
    from app.models.main_task import MainTask

    departments = get_overview_metrics()
    central_department = next((d for d in departments if d.get('is_central')), None)
    report_departments = [d for d in departments if not d.get('is_central')] or departments

    # For each concept dept, aggregate unique "concerned parties" (الجهات المعنية)
    # from the secondary_departments_list JSON across its main tasks.
    stakeholders_by_dept = {}
    for dept in report_departments:
        tasks = MainTask.query.filter_by(primary_department_id=dept['id']).all()
        seen = []
        for t in tasks:
            for name in t.secondary_departments_parsed:
                name = (name or '').strip()
                if name and name not in seen:
                    seen.append(name)
        stakeholders_by_dept[dept['id']] = seen

    return render_template(
        'dashboard/org_structure.html',
        departments=departments,
        central_department=central_department,
        report_departments=report_departments,
        stakeholders_by_dept=stakeholders_by_dept,
        page_title='الهيكل التنظيمي',
    )


@dashboard_bp.route('/agenda')
@login_required
def agenda():
    """Year-2026 agenda calendar — months grid with events, holidays, weekends."""
    from app.dashboard.agenda_service import build_year_calendar
    calendar_data = build_year_calendar(2026)
    return render_template(
        'dashboard/agenda.html',
        calendar=calendar_data,
        page_title='الأجندة السنوية',
    )


@dashboard_bp.route('/agenda/items', methods=['POST'])
@login_required
def create_agenda_item():
    """Create a manually editable agenda item."""
    from app.extensions import db
    from app.models.agenda import AgendaItem

    title = (request.form.get('title') or '').strip()
    event_date = _parse_agenda_date(request.form.get('event_date'))
    color = _clean_agenda_color(request.form.get('color'))
    notes = (request.form.get('notes') or '').strip()

    if not title or event_date is None:
        flash('Please provide an agenda title and date.', 'danger')
        return redirect(url_for('dashboard.agenda'))

    db.session.add(AgendaItem(
        title=title,
        event_date=event_date,
        color=color,
        notes=notes,
        created_by=current_user.id,
    ))
    db.session.commit()
    flash('Agenda item added.', 'success')
    return redirect(url_for('dashboard.agenda'))


@dashboard_bp.route('/agenda/items/<int:item_id>/update', methods=['POST'])
@login_required
def update_agenda_item(item_id):
    """Update an editable agenda item."""
    from app.extensions import db
    from app.models.agenda import AgendaItem

    item = AgendaItem.query.get_or_404(item_id)
    title = (request.form.get('title') or '').strip()
    event_date = _parse_agenda_date(request.form.get('event_date'))

    if not title or event_date is None:
        flash('Please provide an agenda title and date.', 'danger')
        return redirect(url_for('dashboard.agenda'))

    item.title = title
    item.event_date = event_date
    item.color = _clean_agenda_color(request.form.get('color'))
    item.notes = (request.form.get('notes') or '').strip()
    db.session.commit()
    flash('Agenda item updated.', 'success')
    return redirect(url_for('dashboard.agenda'))


@dashboard_bp.route('/agenda/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_agenda_item(item_id):
    """Delete an editable agenda item."""
    from app.extensions import db
    from app.models.agenda import AgendaItem

    item = AgendaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Agenda item deleted.', 'success')
    return redirect(url_for('dashboard.agenda'))


@dashboard_bp.route('/agenda/items/<int:item_id>/move', methods=['POST'])
@login_required
def move_agenda_item(item_id):
    """Move an editable agenda item to another date via drag and drop."""
    from app.extensions import db
    from app.models.agenda import AgendaItem

    item = AgendaItem.query.get_or_404(item_id)
    payload = request.get_json(silent=True) or request.form
    event_date = _parse_agenda_date(payload.get('event_date'))

    if event_date is None:
        return jsonify({'ok': False, 'error': 'Invalid date.'}), 400

    item.event_date = event_date
    db.session.commit()
    return jsonify({
        'ok': True,
        'item': item.to_calendar_dict(),
    })


@dashboard_bp.route('/agenda/items/move', methods=['POST'])
@login_required
def move_any_agenda_item():
    """Move either a custom item or a generated default agenda occurrence."""
    from app.dashboard.agenda_service import EVENT_TYPES
    from app.extensions import db
    from app.models.agenda import AgendaItem

    payload = request.get_json(silent=True) or {}
    item_ref = str(payload.get('item_ref') or '').strip()
    event_date = _parse_agenda_date(payload.get('event_date'))

    if not item_ref or event_date is None:
        return jsonify({'ok': False, 'error': 'Invalid agenda move.'}), 400

    if item_ref.startswith('default::'):
        parts = item_ref.split('::', 2)
        if len(parts) != 3:
            return jsonify({'ok': False, 'error': 'Invalid default event.'}), 400

        event_key = parts[1]
        original_date = _parse_agenda_date(parts[2])
        event_type = EVENT_TYPES.get(event_key)
        if not event_type or original_date is None:
            return jsonify({'ok': False, 'error': 'Unknown default event.'}), 400

        item = AgendaItem.query.filter_by(
            is_default=True,
            event_key=event_key,
            original_date=original_date,
        ).first()
        if item is None:
            item = AgendaItem(
                title=event_type['label'],
                event_date=event_date,
                color=event_type['color'],
                notes='',
                is_default=True,
                event_key=event_key,
                original_date=original_date,
                created_by=current_user.id,
            )
            db.session.add(item)
        else:
            item.event_date = event_date
    else:
        try:
            item_id = int(item_ref)
        except ValueError:
            return jsonify({'ok': False, 'error': 'Invalid item.'}), 400
        item = AgendaItem.query.get_or_404(item_id)
        item.event_date = event_date

    db.session.commit()
    return jsonify({'ok': True, 'item': item.to_calendar_dict()})


@dashboard_bp.route('/agenda/items/save', methods=['POST'])
@login_required
def save_any_agenda_item():
    """Save edits for either a custom item or a generated default occurrence."""
    from app.dashboard.agenda_service import EVENT_TYPES
    from app.extensions import db
    from app.models.agenda import AgendaItem

    item_ref = str(request.form.get('item_ref') or '').strip()
    title = (request.form.get('title') or '').strip()
    event_date = _parse_agenda_date(request.form.get('event_date'))
    color = _clean_agenda_color(request.form.get('color'))
    notes = (request.form.get('notes') or '').strip()

    if not item_ref or not title or event_date is None:
        flash('Please provide an agenda title and date.', 'danger')
        return redirect(url_for('dashboard.agenda'))

    if item_ref.startswith('default::'):
        parts = item_ref.split('::', 2)
        if len(parts) != 3:
            flash('Unable to edit this agenda item.', 'danger')
            return redirect(url_for('dashboard.agenda'))

        event_key = parts[1]
        original_date = _parse_agenda_date(parts[2])
        event_type = EVENT_TYPES.get(event_key)
        if not event_type or original_date is None:
            flash('Unable to edit this agenda item.', 'danger')
            return redirect(url_for('dashboard.agenda'))

        item = AgendaItem.query.filter_by(
            is_default=True,
            event_key=event_key,
            original_date=original_date,
        ).first()
        if item is None:
            item = AgendaItem(
                title=title,
                event_date=event_date,
                color=color or event_type['color'],
                notes=notes,
                is_default=True,
                event_key=event_key,
                original_date=original_date,
                created_by=current_user.id,
            )
            db.session.add(item)
        else:
            item.title = title
            item.event_date = event_date
            item.color = color
            item.notes = notes
    else:
        try:
            item_id = int(item_ref)
        except ValueError:
            flash('Unable to edit this agenda item.', 'danger')
            return redirect(url_for('dashboard.agenda'))
        item = AgendaItem.query.get_or_404(item_id)
        item.title = title
        item.event_date = event_date
        item.color = color
        item.notes = notes

    db.session.commit()
    flash('Agenda item updated.', 'success')
    return redirect(url_for('dashboard.agenda'))


@dashboard_bp.route('/agenda/items/place', methods=['POST'])
@login_required
def place_agenda_item():
    """Place a legend event type onto a selected calendar date."""
    from app.dashboard.agenda_service import EVENT_TYPES
    from app.extensions import db
    from app.models.agenda import AgendaItem

    payload = request.get_json(silent=True) or {}
    event_key = str(payload.get('event_key') or '').strip()
    event_date = _parse_agenda_date(payload.get('event_date'))
    event_type = EVENT_TYPES.get(event_key)

    if not event_type or event_date is None:
        return jsonify({'ok': False, 'error': 'Invalid agenda placement.'}), 400

    item = AgendaItem(
        title=event_type['label'],
        event_date=event_date,
        color=event_type['color'],
        notes='',
        event_key=event_key,
        created_by=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'ok': True, 'item': item.to_calendar_dict()})


def _parse_agenda_date(value):
    try:
        return datetime.strptime(value or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _clean_agenda_color(value):
    value = (value or '#C89B3C').strip()
    if len(value) == 7 and value.startswith('#'):
        try:
            int(value[1:], 16)
            return value.upper()
        except ValueError:
            pass
    return '#C89B3C'


@dashboard_bp.route('/military-strategy-booklet')
@login_required
def strategy_booklet():
    """Military strategy booklet — PDF-style viewer with print-to-PDF download."""
    booklet = {
        'title':    'كراسة الاستراتيجية العسكرية',
        'subtitle': 'الإصدار الأول · 2026',
        'edition':  '2026',
        'foreword': (
            'تمثل هذه الكراسة الإطار المرجعي للاستراتيجية العسكرية الوطنية، '
            'وتجمع بين رؤية القيادة، والأهداف التشغيلية، والمحاور الخمسة '
            'التي تحدد مسار التطوير والجاهزية للمنظومة الدفاعية لدولة الإمارات.'
        ),
        'objectives': [
            'تعزيز أمن الدولة ورفع الجاهزية الاستراتيجية عبر منظومة متكاملة ومرنة.',
            'مواءمة القدرات العسكرية مع الأولويات الوطنية والبنية المؤسسية الحديثة.',
            'تمكين الابتكار والذكاء الاصطناعي والقدرات السيبرانية ضمن إطار تشغيل مستدام.',
            'تنمية الكفاءات الوطنية وتوسيع الشراكات الدولية لدعم التفوق العملياتي.',
            'بناء قاعدة صناعية دفاعية وطنية قادرة على الابتكار والتصدير.',
        ],
        'axes': [
            {
                'title': 'البر',
                'icon':  'bi-shield-fill',
                'desc':  'تعزيز القدرات البرية ورفع الجاهزية الميدانية مع تركيز على المرونة، سرعة الاستجابة، وكفاءة الانتشار التشغيلي.',
                'pillars': ['الجاهزية الميدانية', 'سرعة الانتشار', 'المرونة العملياتية'],
            },
            {
                'title': 'البحر',
                'icon':  'bi-water',
                'desc':  'حماية المصالح البحرية والمسارات الحيوية عبر قدرات مراقبة وسيطرة واستجابة متقدمة ومتكاملة مع شركاء الأمن البحري.',
                'pillars': ['الأمن البحري', 'مراقبة المسارات', 'السيطرة والاستجابة'],
            },
            {
                'title': 'الجو',
                'icon':  'bi-airplane-fill',
                'desc':  'تطوير منظومات التفوق الجوي والدفاع الجوي بما يدعم السيطرة والردع والعمليات المشتركة الحديثة.',
                'pillars': ['التفوق الجوي', 'الدفاع الجوي', 'العمليات المشتركة'],
            },
            {
                'title': 'الفضاء',
                'icon':  'bi-globe2',
                'desc':  'تمكين الاتصالات والاستشعار والمراقبة الفضائية لدعم القرار ورفع دقة الوعي بالمجال العملياتي.',
                'pillars': ['الرصد والاستشعار', 'الاتصالات', 'الوعي العملياتي'],
            },
            {
                'title': 'التقنيات المستقبلية',
                'icon':  'bi-cpu',
                'desc':  'دمج الذكاء الاصطناعي والقدرات السيبرانية والأنظمة غير المأهولة واللوجستيات الذكية ضمن بيئة تشغيلية متطورة.',
                'pillars': ['الذكاء الاصطناعي', 'الأمن السيبراني', 'الأنظمة غير المأهولة'],
            },
        ],
        'closing': (
            'نعمل اليوم برؤية موحدة لبناء غدٍ أكثر أمناً واستقراراً وكفاءة لدولة الإمارات. '
            'تلتقي في هذه الكراسة المبادئ التوجيهية، والخطط التنفيذية، والمعايير الأساسية للجاهزية والتفوق.'
        ),
    }
    return render_template(
        'dashboard/strategy_booklet.html',
        booklet=booklet,
        page_title='كراسة الاستراتيجية العسكرية',
    )


@dashboard_bp.route('/quarterly-performance')
@login_required
def quarterly_performance():
    """Quarterly performance report screen."""
    departments = get_overview_metrics()
    averages = get_company_averages()
    central_department = next((d for d in departments if d.get('is_central')), None)
    report_departments = [d for d in departments if not d.get('is_central')] or departments
    return render_template(
        'dashboard/quarterly_report.html',
        departments=departments,
        central_department=central_department,
        report_departments=report_departments,
        averages=averages,
        page_title='تقرير الأداء الشهري',
    )


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
