"""
MainTask Model — Represents the 'الواجبات الرئيسية' (Main Tasks).
Each task belongs to one primary department but can be linked to multiple secondary departments.
"""

from __future__ import annotations
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.extensions import db


class MainTask(db.Model):
    """
    الواجب الرئيسي (Main Task)
    Example: Task 1.24
    """

    __tablename__ = 'main_tasks'

    id = db.Column(db.Integer, primary_key=True)
    
    # رقم الواجب (e.g. "1.24")
    task_number = db.Column(db.String(50), nullable=False)
    
    # شرح / عنوان الواجب
    description = db.Column(db.Text, nullable=False)
    
    # نسبة الإنجاز المئوية (0-100)
    completion_pct = db.Column(db.Integer, default=0)
    
    # تاريخ النهاية المتوقع
    expected_end_date = db.Column(db.Date, nullable=False)
    
    # الجهة الرئيسية المعنية (Primary Department)
    primary_department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # --- Relationships ---
    
    # Primary Department
    primary_department = db.relationship(
        'Department',
        backref=db.backref('primary_tasks', lazy='dynamic', cascade='all, delete-orphan')
    )
    
    # Secondary/Involved Departments (الجهات المشتركة)
    # Stored as a JSON string list of department names: ["المالية", "الموارد البشرية"]
    secondary_departments_list = db.Column(db.Text, default='[]')

    def __repr__(self) -> str:
        return f'<MainTask {self.task_number}: {self.description[:20]}>'

    @property
    def is_overdue_5_years(self) -> bool:
        """
        Check if the expected end date is more than 5 years from creation.
        Returns True if difference > 5 years.
        """
        if not self.expected_end_date or not self.created_at:
            return False
            
        # Convert created_at to date for comparison
        created_date = self.created_at.date()
        max_allowed_date = created_date + relativedelta(years=5)
        
        return self.expected_end_date > max_allowed_date

    @property
    def secondary_departments_parsed(self) -> list:
        """Parse the JSON string into a Python list."""
        import json
        if not self.secondary_departments_list:
            return []
        try:
            return json.loads(self.secondary_departments_list)
        except Exception:
            return []
