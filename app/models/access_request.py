"""
Access Request Model — Multi-level approval workflow.

Flow: User → Group Admin (60) → Deputy (80) → Secretary (90) → Director (100)
Any level can reject with mandatory reason.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional

from app.extensions import db


class AccessRequest(db.Model):
    """
    User's request for elevated access or permissions.
    Flows up the organizational hierarchy for approval.
    """

    __tablename__ = 'access_requests'

    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    id                     = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id           = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    requested_role_code    = db.Column(db.String(30), nullable=False)
    requested_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    justification          = db.Column(db.Text, nullable=False)
    status                 = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    current_approver_level = db.Column(db.Integer, default=60)  # Starts at GROUP_ADMIN
    created_at             = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at            = db.Column(db.DateTime, nullable=True)

    # Relationships
    requester   = db.relationship('User', foreign_keys=[requester_id])
    department  = db.relationship('Department', foreign_keys=[requested_department_id])
    approvals   = db.relationship('AccessApproval', back_populates='request',
                                  cascade='all, delete-orphan', order_by='AccessApproval.decided_at')

    def __repr__(self) -> str:
        return f'<AccessRequest {self.id[:8]} [{self.status}]>'

    def is_pending(self) -> bool:
        return self.status == self.STATUS_PENDING

    def approve_at_level(self, approver_user, next_level: Optional[int]) -> None:
        """
        Record approval at current level and advance to next level.
        If next_level is None the request is fully approved.
        """
        from app.models.audit import AuditLog
        approval = AccessApproval(
            request_id          = self.id,
            approver_id         = approver_user.id,
            approver_role_level = approver_user.permission_level,
            decision            = AccessApproval.DECISION_APPROVED,
        )
        db.session.add(approval)

        if next_level is None:
            self.status      = self.STATUS_APPROVED
            self.resolved_at = datetime.utcnow()
        else:
            self.current_approver_level = next_level

        db.session.commit()

    def reject_at_level(self, approver_user, reason: str) -> None:
        """Record rejection — requires a reason string."""
        approval = AccessApproval(
            request_id          = self.id,
            approver_id         = approver_user.id,
            approver_role_level = approver_user.permission_level,
            decision            = AccessApproval.DECISION_REJECTED,
            rejection_reason    = reason,
        )
        db.session.add(approval)
        self.status      = self.STATUS_REJECTED
        self.resolved_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self) -> dict:
        return {
            'id':                      self.id,
            'requester':               self.requester.full_name if self.requester else '',
            'requested_role':          self.requested_role_code,
            'justification':           self.justification,
            'status':                  self.status,
            'current_approver_level':  self.current_approver_level,
            'created_at':              self.created_at.isoformat() if self.created_at else None,
        }


class AccessApproval(db.Model):
    """Single approval/rejection record from one level."""

    __tablename__ = 'access_approvals'

    DECISION_APPROVED = 'approved'
    DECISION_REJECTED = 'rejected'

    id                  = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id          = db.Column(db.String(36), db.ForeignKey('access_requests.id'), nullable=False)
    approver_id         = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    approver_role_level = db.Column(db.Integer, nullable=False)
    decision            = db.Column(db.String(20), nullable=False)
    rejection_reason    = db.Column(db.Text, nullable=True)
    decided_at          = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    request  = db.relationship('AccessRequest', back_populates='approvals')
    approver = db.relationship('User')
