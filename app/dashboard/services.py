"""Dashboard services — data fetching and metrics computation."""

from __future__ import annotations
from typing import List, Dict

from app.models.department import Department
from app.models.duties import Duty
from app.models.main_task import MainTask


def get_overview_metrics() -> List[Dict]:
    """
    Return list of depts with current competence% and completion%.
    Used by the CEO spider-web dashboard.
    """
    depts = Department.active_ordered()
    result = []
    for d in depts:
        result.append({
            'id':                 d.id,
            'code':               d.code,
            'name':               d.name,
            'color':              d.color,
            'icon':               d.icon,
            'logo_file':          d.logo_file,
            'description':        d.description,
            'responsible_person': d.responsible_person,
            'responsible_name':   d.responsible_name,
            'concept_number':     getattr(d, 'concept_number', None),
            'is_central':         bool(d.is_central),
            'director_notes':     d.director_notes or '',
            'competence_pct':     d.competence_pct(),
            'completion_pct':     d.completion_pct(),
            'duties_count':       MainTask.query.filter_by(primary_department_id=d.id).count(),
        })
    return result



def get_company_averages() -> Dict[str, float]:
    """Compute company-wide averages for both metrics."""
    depts = Department.active_ordered()
    if not depts:
        return {'competence': 0.0, 'completion': 0.0}

    avg_comp = sum(d.competence_pct() for d in depts) / len(depts)
    avg_done = sum(d.completion_pct() for d in depts) / len(depts)
    return {'competence': round(avg_comp, 1), 'completion': round(avg_done, 1)}
