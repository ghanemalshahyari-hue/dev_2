"""
Role Model — Defines permission levels for the organizational hierarchy.
Roles are stored in the DB so they can be edited from the admin UI.
"""

from __future__ import annotations
from typing import Optional

from app.extensions import db


class Role(db.Model):
    """
    Organizational role with permission level.
    Stored in DB so admins can adjust without code changes.
    """

    __tablename__ = 'roles'

    id               = db.Column(db.Integer, primary_key=True)
    code             = db.Column(db.String(30), unique=True, nullable=False)
    name             = db.Column(db.String(80), nullable=False)
    name_ar          = db.Column(db.String(80), nullable=False, default='')
    permission_level = db.Column(db.Integer, nullable=False)
    description      = db.Column(db.Text, default='')
    is_system        = db.Column(db.Boolean, default=False)  # Cannot be deleted

    # Relationships
    users = db.relationship('User', back_populates='role', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<Role {self.code}:{self.permission_level}>'

    def can(self, required_level: int) -> bool:
        """Check if this role meets the required permission level."""
        return self.permission_level >= required_level

    @classmethod
    def get_by_code(cls, code: str) -> Optional['Role']:
        return cls.query.filter_by(code=code).first()

    @classmethod
    def get_by_level(cls, level: int) -> Optional['Role']:
        return cls.query.filter_by(permission_level=level).first()

    @classmethod
    def create_default_roles(cls) -> None:
        """Seed default roles if they don't exist."""
        defaults = [
            {
                'code': 'DEVELOPER',
                'name': 'Developer',
                'name_ar': 'المطور',
                'permission_level': 999,
                'description': 'Full system access for developers and testing.',
                'is_system': True,
            },
            {
                'code': 'DIRECTOR',
                'name': 'Director',
                'name_ar': 'المدير',
                'permission_level': 100,
                'description': 'CEO-level overview: sees the circular dashboard with all 7 groups.',
                'is_system': True,
            },
            {
                'code': 'SECRETARY',
                'name': 'Secretary',
                'name_ar': 'السكرتير',
                'permission_level': 90,
                'description': 'Plans and coordinates groups, manages 5-year timeline, workshops, and forms.',
                'is_system': True,
            },
            {
                'code': 'DEPUTY',
                'name': 'Deputy Director',
                'name_ar': 'نائب المدير',
                'permission_level': 80,
                'description': 'Makes decisions and approvals based on the Secretary\'s plans.',
                'is_system': True,
            },
            {
                'code': 'GROUP_ADMIN',
                'name': 'Group Administrator',
                'name_ar': 'مدير المجموعة',
                'permission_level': 60,
                'description': 'Manages one group: data entry, reports, and metrics.',
                'is_system': True,
            },
            {
                'code': 'USER',
                'name': 'User',
                'name_ar': 'مستخدم',
                'permission_level': 20,
                'description': 'View personal data, submit access requests.',
                'is_system': True,
            },
        ]

        for data in defaults:
            if not cls.query.filter_by(code=data['code']).first():
                role = cls(**data)
                db.session.add(role)

        db.session.commit()


# ─── Permission level constants ───────────────────────────────────────────────
PERMISSIONS = {
    'DEVELOPER':   999,
    'DIRECTOR':    100,
    'SECRETARY':    90,
    'DEPUTY':       80,
    'GROUP_ADMIN':  60,
    'USER':         20,
}
