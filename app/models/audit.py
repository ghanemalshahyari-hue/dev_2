"""
Audit Log Model — Immutable record of all system actions.
Every important event is logged here for compliance and security review.
"""

from __future__ import annotations
import uuid
from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    """
    Immutable audit trail. Never update or delete records in this table.
    """

    __tablename__ = 'audit_log'

    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    username      = db.Column(db.String(80),  nullable=False, default='anonymous')  # Snapshot
    action        = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(60),  nullable=True)
    resource_id   = db.Column(db.String(36),  nullable=True)
    details       = db.Column(db.Text, nullable=True)   # JSON string for old/new values
    ip_address    = db.Column(db.String(45),  nullable=True)
    user_agent    = db.Column(db.String(255), nullable=True)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = db.relationship('User', back_populates='audit_logs', foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f'<AuditLog {self.action} by {self.username} @ {self.timestamp}>'

    def to_dict(self) -> dict:
        return {
            'id':            self.id,
            'username':      self.username,
            'action':        self.action,
            'resource_type': self.resource_type,
            'resource_id':   self.resource_id,
            'details':       self.details,
            'ip_address':    self.ip_address,
            'timestamp':     self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        resource_type: str = None,
        resource_id: str = None,
        details: str = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> 'AuditLog':
        """
        Create and persist an audit log entry.

        Usage:
            AuditLog.log('user.login', user=current_user, ip_address=request.remote_addr)
        """
        entry = cls(
            user_id       = user.id if user else None,
            username      = user.username if user else 'anonymous',
            action        = action,
            resource_type = resource_type,
            resource_id   = str(resource_id) if resource_id else None,
            details       = details,
            ip_address    = ip_address,
            user_agent    = user_agent,
        )
        db.session.add(entry)
        db.session.commit()
        return entry
