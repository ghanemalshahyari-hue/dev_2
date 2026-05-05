"""
Department Metrics Model

Stores competence and completion percentages for CEO dashboard.
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from app.extensions import db


class DepartmentMetrics(db.Model):
    """
    Department performance metrics for dashboard.
    
    Two key metrics per department:
    1. Competence % - Quality of data provided
    2. Completion % - Data entry completion status
    
    Attributes:
        id: UUID primary key
        department_id: Department these metrics belong to
        metric_date: Date of this metric snapshot
        competence_percentage: Data quality score (0-100)
        completion_percentage: Data entry completion (0-100)
        data_entries_required: Total required entries
        data_entries_completed: Completed entries
        quality_score: Additional quality metric
        notes: Optional notes about this snapshot
        updated_by: User who updated these metrics
        updated_at: Last update timestamp
    """
    
    __tablename__ = 'department_metrics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, index=True)
    metric_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    
    # Core metrics
    competence_percentage = db.Column(db.Float, default=0.0, nullable=False)
    completion_percentage = db.Column(db.Float, default=0.0, nullable=False)
    
    # Detailed metrics
    data_entries_required = db.Column(db.Integer, default=0, nullable=False)
    data_entries_completed = db.Column(db.Integer, default=0, nullable=False)
    quality_score = db.Column(db.Float, default=0.0, nullable=False)
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', back_populates='metrics')
    updater = db.relationship('User', foreign_keys=[updated_by])
    
    # Unique constraint: one metric per department per day
    __table_args__ = (
        db.UniqueConstraint('department_id', 'metric_date', name='uq_department_date'),
    )
    
    def __repr__(self) -> str:
        return f'<DepartmentMetrics {self.department.code if self.department else "?"} {self.metric_date}>'
    
    @property
    def calculated_completion(self) -> float:
        """Calculate completion percentage from entries."""
        if self.data_entries_required == 0:
            return 0.0
        return (self.data_entries_completed / self.data_entries_required) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'department_id': self.department_id,
            'department_code': self.department.code if self.department else None,
            'department_name': self.department.name if self.department else None,
            'metric_date': self.metric_date.isoformat(),
            'competence_percentage': round(self.competence_percentage, 2),
            'completion_percentage': round(self.completion_percentage, 2),
            'data_entries_required': self.data_entries_required,
            'data_entries_completed': self.data_entries_completed,
            'quality_score': round(self.quality_score, 2),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_latest_for_all_departments(cls) -> List['DepartmentMetrics']:
        """Get latest metrics for all departments."""
        from app.models.department import Department
        
        # Subquery to get max date per department
        from sqlalchemy import func
        subquery = db.session.query(
            cls.department_id,
            func.max(cls.metric_date).label('max_date')
        ).group_by(cls.department_id).subquery()
        
        # Join to get latest metrics
        return cls.query.join(
            subquery,
            db.and_(
                cls.department_id == subquery.c.department_id,
                cls.metric_date == subquery.c.max_date
            )
        ).join(Department).filter(
            Department.is_active == True
        ).order_by(Department.order_index).all()
    
    @classmethod
    def get_or_create_today(cls, department_id: int, user_id: str = None) -> 'DepartmentMetrics':
        """Get today's metrics or create new entry."""
        today = date.today()
        metrics = cls.query.filter_by(
            department_id=department_id,
            metric_date=today
        ).first()
        
        if not metrics:
            metrics = cls(
                department_id=department_id,
                metric_date=today,
                updated_by=user_id
            )
            db.session.add(metrics)
            db.session.commit()
        
        return metrics
    
    @classmethod
    def update_metrics(
        cls,
        department_id: int,
        competence: float = None,
        completion: float = None,
        entries_required: int = None,
        entries_completed: int = None,
        quality: float = None,
        notes: str = None,
        user_id: str = None
    ) -> 'DepartmentMetrics':
        """Update or create today's metrics for a department."""
        metrics = cls.get_or_create_today(department_id, user_id)
        
        if competence is not None:
            metrics.competence_percentage = max(0, min(100, competence))
        if completion is not None:
            metrics.completion_percentage = max(0, min(100, completion))
        if entries_required is not None:
            metrics.data_entries_required = max(0, entries_required)
        if entries_completed is not None:
            metrics.data_entries_completed = max(0, entries_completed)
        if quality is not None:
            metrics.quality_score = max(0, min(100, quality))
        if notes is not None:
            metrics.notes = notes
        if user_id:
            metrics.updated_by = user_id
        
        db.session.commit()
        return metrics
    
    @classmethod
    def get_company_overview(cls) -> Dict:
        """Get company-wide metrics summary."""
        all_metrics = cls.get_latest_for_all_departments()
        
        if not all_metrics:
            return {
                'avg_competence': 0.0,
                'avg_completion': 0.0,
                'total_departments': 0,
                'departments': []
            }
        
        total_competence = sum(m.competence_percentage for m in all_metrics)
        total_completion = sum(m.completion_percentage for m in all_metrics)
        count = len(all_metrics)
        
        return {
            'avg_competence': round(total_competence / count, 2),
            'avg_completion': round(total_completion / count, 2),
            'total_departments': count,
            'departments': [m.to_dict() for m in all_metrics]
        }
