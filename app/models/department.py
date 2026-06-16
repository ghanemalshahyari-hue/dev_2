"""
Department Model — Represents the 7 (configurable) organizational groups.
Groups can be added, removed, hidden, or reordered entirely from the admin UI.
"""

from __future__ import annotations
from typing import List, Optional

from app.extensions import db


class Department(db.Model):
    """
    Organizational group / department.
    Fully manageable from the admin panel without code changes.
    """

    __tablename__ = 'departments'

    id                 = db.Column(db.Integer, primary_key=True)
    code               = db.Column(db.String(20), unique=True, nullable=False)
    name               = db.Column(db.String(120), nullable=False)
    description        = db.Column(db.Text, default='')
    responsible_person = db.Column(db.String(120), default='')          # Title / role (e.g., "رئيس هيئة...")
    responsible_name   = db.Column(db.String(120), default='')          # Person's name (shown above the title)
    color              = db.Column(db.String(7), default='#4F8EF7')   # Hex color
    icon               = db.Column(db.String(60), default='bi-grid-fill')
    logo_file          = db.Column(db.String(120), nullable=True)     # Custom logo filename
    concept_number     = db.Column(db.Integer, nullable=True)         # Operational Concept Number
    order_index        = db.Column(db.Integer, default=0)
    is_active          = db.Column(db.Boolean, default=True, nullable=False)
    is_central         = db.Column(db.Boolean, default=False, nullable=False)  # CEO hub group
    director_notes     = db.Column(db.Text, default='')               # Inline CEO notes
    concept_number     = db.Column(db.Integer, nullable=True)         # المفهوم العملياتي المشترك عدد
    created_at         = db.Column(db.DateTime, server_default=db.func.now())
    updated_at         = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


    # Relationships
    users   = db.relationship('User', back_populates='department', lazy='dynamic')
    metrics = db.relationship('DepartmentMetrics', back_populates='department',
                              lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Department {self.code}: {self.name}>'

    def latest_metrics(self) -> Optional['DepartmentMetrics']:
        """Return the most recent metrics entry."""
        return (
            self.metrics
            .order_by(DepartmentMetrics.metric_date.desc())
            .first()
        )

    def competence_pct(self) -> float:
        m = self.latest_metrics()
        return float(m.competence_percentage) if m else 0.0

    def completion_pct(self) -> float:
        m = self.latest_metrics()
        return float(m.completion_percentage) if m else 0.0

    def to_dict(self) -> dict:
        return {
            'id':                 self.id,
            'code':               self.code,
            'name':               self.name,
            'description':        self.description,
            'responsible_person': self.responsible_person,
            'color':              self.color,
            'icon':               self.icon,
            'logo_file':          self.logo_file,
            'order_index':        self.order_index,
            'is_active':          self.is_active,
            'is_central':         self.is_central,
            'director_notes':     self.director_notes or '',
            'competence_pct':     self.competence_pct(),
            'completion_pct':     self.completion_pct(),
        }

    @classmethod
    def active_ordered(cls) -> List['Department']:
        """Return visible departments sorted by order_index."""
        return cls.query.filter_by(is_active=True).order_by(cls.order_index).all()

    @classmethod
    def create_default_departments(cls) -> None:
        """Seed default departments if table is empty."""
        from flask import current_app

        if cls.query.count() > 0:
            return

        defaults = current_app.config.get('DEFAULT_DEPARTMENTS', [])
        for i, d in enumerate(defaults):
            dept = cls(
                code=d['code'],
                name=d['name'],
                color=d['color'],
                icon=d['icon'],
                order_index=d['order_index'],
                description='',
                responsible_person='',
                is_central=(i == 0),   # First dept in config is the strategic center
                director_notes='',
            )
            db.session.add(dept)

        db.session.commit()


class DepartmentMetrics(db.Model):
    """Time-series metrics for each department."""

    __tablename__ = 'department_metrics'

    id                    = db.Column(db.Integer, primary_key=True)
    department_id         = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    metric_date           = db.Column(db.Date, nullable=False, server_default=db.func.current_date())
    competence_percentage = db.Column(db.Numeric(5, 2), default=0.0)
    completion_percentage = db.Column(db.Numeric(5, 2), default=0.0)
    notes                 = db.Column(db.Text, default='')
    updated_by_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at            = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    department = db.relationship('Department', back_populates='metrics')
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def to_dict(self) -> dict:
        return {
            'id':                    self.id,
            'department_id':         self.department_id,
            'metric_date':           str(self.metric_date),
            'competence_percentage': float(self.competence_percentage),
            'completion_percentage': float(self.completion_percentage),
            'notes':                 self.notes,
        }
