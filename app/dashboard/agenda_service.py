"""
Agenda calendar service — builds the 12-month grid for a given year.

Marks weekends (Saturday + Sunday), official UAE holidays (Eid Al-Fitr,
Eid Al-Adha, etc.), and the recurring schedule of reports and meetings.

Event types and their colors are defined in EVENT_TYPES — adjust here to
change the legend or the recurrence rules.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Dict, List

from app.models.agenda import AgendaItem


# ── Arabic month names ────────────────────────────────────────────────
ARABIC_MONTHS = [
    'يناير', 'فبراير', 'مارس', 'أبريل',
    'مايو', 'يونيو', 'يوليو', 'أغسطس',
    'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر',
]

# Arabic day names — Monday-first (ISO week convention)
ARABIC_DAYS_MON_FIRST = ['إثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة', 'سبت', 'أحد']


# ── Event types (legend keys → display + color) ───────────────────────
EVENT_TYPES = {
    'monthly_report': {
        'label': 'تقرير الأداء الشهري',
        'color': '#DC2626',          # red
        'icon': 'bi-file-earmark-bar-graph',
    },
    'strategic_report': {
        'label': 'تقرير الأداء الشهري الاستراتيجي',
        'color': '#2563EB',          # blue
        'icon': 'bi-bullseye',
    },
    'office_report': {
        'label': 'تقرير الأداء الشهري للمكتب',
        'color': '#7C3AED',          # purple
        'icon': 'bi-briefcase',
    },
    'secretariat_meeting': {
        'label': 'اجتماع السكرتارية',
        'color': '#16A34A',          # green
        'icon': 'bi-people',
    },
    'strategy_meeting': {
        'label': 'اجتماع فريق الاستراتيجية',
        'color': '#8B5A2B',          # brown
        'icon': 'bi-diagram-3',
    },
}


# ── UAE public holidays for 2026 (lunar dates are approximate) ────────
def _build_holidays_2026() -> Dict[date, str]:
    return {
        date(2026, 1, 1):  'رأس السنة الميلادية',
        # Eid Al-Fitr 2026 — approximate (Mar 20–22)
        date(2026, 3, 20): 'عيد الفطر',
        date(2026, 3, 21): 'عيد الفطر',
        date(2026, 3, 22): 'عيد الفطر',
        # Arafat Day + Eid Al-Adha 2026 — approximate (May 26–29)
        date(2026, 5, 26): 'يوم عرفة',
        date(2026, 5, 27): 'عيد الأضحى',
        date(2026, 5, 28): 'عيد الأضحى',
        date(2026, 5, 29): 'عيد الأضحى',
        # Hijri New Year (approximate)
        date(2026, 6, 16): 'رأس السنة الهجرية',
        # Prophet's Birthday (approximate)
        date(2026, 8, 25): 'المولد النبوي',
        # UAE Commemoration & National Day
        date(2026, 12, 1): 'يوم الشهيد',
        date(2026, 12, 2): 'اليوم الوطني',
        date(2026, 12, 3): 'اليوم الوطني',
    }


# ── Event schedule rules ──────────────────────────────────────────────
# Tweak these to change when each event recurs across the year.

def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return last occurrence of `weekday` (Mon=0..Sun=6) in given month."""
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _first_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return first occurrence of `weekday` in given month."""
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


def _build_events_2026(holidays: Dict[date, str]) -> Dict[date, List[str]]:
    """
    Generate the default recurring schedule for 2026.

    Rules (all skip official holidays automatically — events on a holiday
    are shifted to the next non-holiday weekday):

    - monthly_report      → last Thursday of each month
    - strategic_report    → 5th of each month
    - office_report       → 15th of each month
    - secretariat_meeting → every Sunday
    - strategy_meeting    → first Wednesday of each month
    """
    events: Dict[date, List[str]] = {}

    def add(d: date, key: str) -> None:
        # Skip events that land on official holidays (keep the day clean)
        if d in holidays:
            return
        events.setdefault(d, []).append(key)

    year = 2026
    for m in range(1, 13):
        # Monthly performance report — last Thursday (weekday 3)
        add(_last_weekday_of_month(year, m, 3), 'monthly_report')

        # Strategic monthly report — 5th of the month
        try:
            add(date(year, m, 5), 'strategic_report')
        except ValueError:
            pass

        # Office monthly report — 15th of the month
        try:
            add(date(year, m, 15), 'office_report')
        except ValueError:
            pass

        # Strategy team meeting — first Wednesday (weekday 2)
        add(_first_weekday_of_month(year, m, 2), 'strategy_meeting')

    # Secretariat meeting — every Sunday across the whole year
    d = date(year, 1, 1)
    while d.year == year:
        if d.weekday() == 6:  # Sunday
            add(d, 'secretariat_meeting')
        d += timedelta(days=1)

    return events


# ── Public API ────────────────────────────────────────────────────────

def build_year_calendar(year: int = 2026) -> dict:
    """
    Build the complete year-grid payload consumed by the agenda template.

    Returns:
        {
            'year': int,
            'day_headers': [...],
            'months': [
                {
                    'name': 'يناير',
                    'number': 1,
                    'weeks': [
                        [day_dict, day_dict, ...],   # 7 cells, Sun-first
                        ...
                    ],
                    'event_count': int,
                },
                ...
            ],
            'legend': [{'key', 'label', 'color', 'icon'}, ...],
            'holidays': [{'date', 'name'}, ...],   # sorted
        }

    Each day_dict has:
        day, date_iso, in_month, is_weekend, holiday (str|None), events (list)
    """
    holidays = _build_holidays_2026() if year == 2026 else {}
    events_by_date = _build_events_2026(holidays) if year == 2026 else {}
    agenda_items = AgendaItem.query.filter(
        AgendaItem.event_date >= date(year, 1, 1),
        AgendaItem.event_date <= date(year, 12, 31),
    ).order_by(AgendaItem.event_date.asc(), AgendaItem.created_at.asc()).all()
    default_overrides = [item for item in agenda_items if item.is_default]
    custom_items = [item for item in agenda_items if not item.is_default]

    for item in default_overrides:
        if item.original_date and item.event_key:
            original_events = events_by_date.get(item.original_date, [])
            events_by_date[item.original_date] = [
                key for key in original_events if key != item.event_key
            ]

    custom_by_date: Dict[date, List[dict]] = {}
    for item in custom_items:
        custom_by_date.setdefault(item.event_date, []).append(item.to_calendar_dict())
    for item in default_overrides:
        custom_by_date.setdefault(item.event_date, []).append(item.to_calendar_dict())

    # Monday-first week (ISO convention)
    cal = calendar.Calendar(firstweekday=0)

    months_data = []
    for m in range(1, 13):
        weeks_out: List[List[dict]] = []
        month_event_count = 0

        for week in cal.monthdatescalendar(year, m):
            row: List[dict] = []
            for d in week:
                in_month = d.month == m
                weekday = d.weekday()  # Mon=0 .. Sun=6
                is_weekend = weekday in (5, 6)  # Sat=5, Sun=6
                holiday_name = holidays.get(d) if in_month else None
                day_events = events_by_date.get(d, []) if in_month else []
                day_default_items = []
                for event_key in day_events:
                    event_type = EVENT_TYPES[event_key]
                    day_default_items.append({
                        'id': f'default::{event_key}::{d.isoformat()}',
                        'title': event_type['label'],
                        'date': d.isoformat(),
                        'color': event_type['color'],
                        'notes': '',
                        'is_default': True,
                        'event_key': event_key,
                        'original_date': d.isoformat(),
                    })
                day_custom_items = custom_by_date.get(d, []) if in_month else []
                day_visible_items = day_default_items + day_custom_items
                if in_month:
                    month_event_count += len(day_visible_items)
                row.append({
                    'day': d.day,
                    'date_iso': d.isoformat(),
                    'in_month': in_month,
                    'is_weekend': is_weekend,
                    'holiday': holiday_name,
                    'events': day_events,
                    'custom_items': day_visible_items,
                })
            weeks_out.append(row)

        months_data.append({
            'name': ARABIC_MONTHS[m - 1],
            'number': m,
            'weeks': weeks_out,
            'event_count': month_event_count,
        })

    legend = [
        {'key': k, **v} for k, v in EVENT_TYPES.items()
    ]

    # Flat dict for quick lookups inside the template (legend_map[event_key].label)
    legend_map = {k: {'key': k, **v} for k, v in EVENT_TYPES.items()}

    holiday_list = sorted(
        [{'date': d.isoformat(), 'name': name} for d, name in holidays.items()],
        key=lambda h: h['date'],
    )

    return {
        'year': year,
        'day_headers': ARABIC_DAYS_MON_FIRST,
        'months': months_data,
        'legend': legend,
        'legend_map': legend_map,
        'holidays': holiday_list,
        'custom_items': [item.to_calendar_dict() for item in custom_items],
    }
