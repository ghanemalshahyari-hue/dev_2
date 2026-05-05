"""
User Model — LDAP-linked enterprise user.
Supports both LDAP authentication and local dev accounts (Argon2 hash).
"""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from typing import Optional

from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    """
    Application user linked to LDAP directory.
    In dev/sim mode local Argon2 password hash is used.
    """

    __tablename__ = 'users'

    id              = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ldap_dn         = db.Column(db.String(255), unique=True, nullable=True)
    username        = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email           = db.Column(db.String(120), nullable=False)
    full_name       = db.Column(db.String(120), nullable=False)
    password_hash   = db.Column(db.String(255), nullable=True)  # Only for sim mode
    is_ldap_user    = db.Column(db.Boolean, default=True)
    is_active       = db.Column(db.Boolean, default=True)

    role_id         = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    # Login security
    failed_logins     = db.Column(db.Integer, default=0)
    locked_until      = db.Column(db.DateTime, nullable=True)

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login  = db.Column(db.DateTime, nullable=True)

    # Relationships
    role       = db.relationship('Role', back_populates='users')
    department = db.relationship('Department', back_populates='users')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic',
                                 foreign_keys='AuditLog.user_id')

    def __repr__(self) -> str:
        return f'<User {self.username} [{self.role.code if self.role else "NO_ROLE"}]>'

    # ── Flask-Login interface ─────────────────────────────────────────────────

    def get_id(self) -> str:
        return self.id

    @property
    def is_authenticated(self) -> bool:
        return True

    # ── Auth helpers ─────────────────────────────────────────────────────────

    def set_password(self, password: str) -> None:
        """Hash password with Argon2 (for dev/sim accounts)."""
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        """Verify Argon2 password hash."""
        if not self.password_hash:
            return False
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError
        ph = PasswordHasher()
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False

    def is_locked_out(self) -> bool:
        """Return True if account is currently locked."""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        """Increment failed login counter and lock if threshold hit."""
        self.failed_logins = (self.failed_logins or 0) + 1
        if self.failed_logins >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        db.session.commit()

    def record_successful_login(self) -> None:
        """Reset failed logins and update last_login."""
        self.failed_logins = 0
        self.locked_until  = None
        self.last_login    = datetime.utcnow()
        db.session.commit()

    # ── Permission helpers ────────────────────────────────────────────────────

    def has_permission(self, required_level: int) -> bool:
        if not self.role:
            return False
        return self.role.permission_level >= required_level

    @property
    def permission_level(self) -> int:
        return self.role.permission_level if self.role else 0

    @property
    def role_code(self) -> str:
        return self.role.code if self.role else 'USER'

    def is_developer(self) -> bool:
        return self.role_code == 'DEVELOPER'

    def is_director(self) -> bool:
        return self.role_code in ('DIRECTOR', 'DEVELOPER')

    def is_secretary(self) -> bool:
        return self.role_code in ('SECRETARY', 'DEVELOPER')

    def is_deputy(self) -> bool:
        return self.role_code in ('DEPUTY', 'DEVELOPER')

    def is_group_admin(self) -> bool:
        return self.role_code in ('GROUP_ADMIN', 'DEVELOPER')

    def can_admin(self) -> bool:
        """Can manage users, departments, roles."""
        return self.permission_level >= 80  # Deputy and above

    def to_dict(self) -> dict:
        return {
            'id':            self.id,
            'username':      self.username,
            'email':         self.email,
            'full_name':     self.full_name,
            'role':          self.role.code if self.role else None,
            'role_display':  self.role.name_ar if self.role else '',
            'department_id': self.department_id,
            'department':    self.department.name if self.department else '',
            'is_active':     self.is_active,
            'last_login':    self.last_login.isoformat() if self.last_login else None,
        }

    # ── Class helpers ─────────────────────────────────────────────────────────

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        return cls.query.filter_by(username=username.lower()).first()

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        return cls.query.get(user_id)
