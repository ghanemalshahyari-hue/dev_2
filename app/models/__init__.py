"""Models package — imports all models so SQLAlchemy sees them."""

from app.models.role import Role, PERMISSIONS
from app.models.user import User
from app.models.department import Department, DepartmentMetrics
from app.models.main_task import MainTask
from app.models.access_request import AccessRequest, AccessApproval
from app.models.audit import AuditLog
from app.models.agenda import AgendaItem

__all__ = [
    'Role', 'PERMISSIONS',
    'User',
    'Department', 'DepartmentMetrics',
    'MainTask',
    'AccessRequest', 'AccessApproval',
    'AuditLog',
    'AgendaItem',
]
