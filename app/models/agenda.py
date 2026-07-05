"""Editable agenda items shown on the annual calendar."""

from __future__ import annotations

from datetime import datetime

from app.extensions import db


class AgendaItem(db.Model):
    """A manually managed agenda item for a specific calendar date."""

    __tablename__ = 'agenda_items'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False, index=True)
    color = db.Column(db.String(7), nullable=False, default='#C89B3C')
    notes = db.Column(db.Text, default='')
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    event_key = db.Column(db.String(80), nullable=True)
    original_date = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f'<AgendaItem {self.event_date}: {self.title}>'

    def to_calendar_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'date': self.event_date.isoformat(),
            'color': self.color,
            'notes': self.notes or '',
            'is_default': bool(self.is_default),
            'event_key': self.event_key or '',
            'original_date': self.original_date.isoformat() if self.original_date else '',
        }
