"""
Planning Models - نماذج التخطيط

هذا الملف يحتوي على النماذج المتعلقة بوظائف السكرتير:
- Timeline (الإطار الزمني)
- Plan (الخطط الشهرية والسنوية)
- Workshop (ورش العمل)
- Template (النماذج)
- Directive (التوجيهات)
- Alert (التنبيهات)
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from app.extensions import db


class PlanType(str, Enum):
    """نوع الخطة"""
    MONTHLY = 'monthly'      # شهري
    QUARTERLY = 'quarterly'  # ربع سنوي
    YEARLY = 'yearly'        # سنوي


class PlanStatus(str, Enum):
    """حالة الخطة"""
    DRAFT = 'draft'          # مسودة
    ACTIVE = 'active'        # نشط
    COMPLETED = 'completed'  # مكتمل
    CANCELLED = 'cancelled'  # ملغي


class Plan(db.Model):
    """
    الخطة (شهرية/ربع سنوية/سنوية)
    
    يستخدمها السكرتير لتتبع الإطار الزمني.
    """
    
    __tablename__ = 'plans'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # عنوان الخطة
    description = db.Column(db.Text)  # وصف الخطة
    plan_type = db.Column(db.String(20), default=PlanType.YEARLY.value)  # نوع الخطة
    
    # الفترة الزمنية
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    year = db.Column(db.Integer, nullable=False)  # السنة
    month = db.Column(db.Integer, nullable=True)  # الشهر (للخطط الشهرية)
    quarter = db.Column(db.Integer, nullable=True)  # الربع (للخطط الربع سنوية)
    
    # الحالة والتقدم
    status = db.Column(db.String(20), default=PlanStatus.DRAFT.value)
    progress_percentage = db.Column(db.Float, default=0.0)  # نسبة التقدم
    
    # المجموعة المرتبطة (اختياري)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # المنشئ والتواريخ
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', backref='plans')
    goals = db.relationship('PlanGoal', backref='plan', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self) -> str:
        return f'<Plan {self.title} ({self.year})>'
    
    def update_progress(self):
        """تحديث نسبة التقدم بناءً على الأهداف"""
        total_goals = self.goals.count()
        if total_goals == 0:
            self.progress_percentage = 0.0
            return
        
        completed_goals = self.goals.filter_by(is_completed=True).count()
        self.progress_percentage = (completed_goals / total_goals) * 100
        db.session.commit()


class PlanGoal(db.Model):
    """
    هدف ضمن خطة
    """
    
    __tablename__ = 'plan_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)  # عنوان الهدف
    description = db.Column(db.Text)  # وصف الهدف
    target_value = db.Column(db.Float, nullable=True)  # القيمة المستهدفة
    current_value = db.Column(db.Float, default=0.0)  # القيمة الحالية
    is_completed = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.Date, nullable=True)  # تاريخ الاستحقاق
    completed_at = db.Column(db.DateTime, nullable=True)
    
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f'<PlanGoal {self.title}>'
    
    def mark_completed(self):
        """تحديد الهدف كمكتمل"""
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        db.session.commit()
        # تحديث تقدم الخطة
        from app.models.planning import Plan
        plan = Plan.query.get(self.plan_id)
        if plan:
            plan.update_progress()


class Workshop(db.Model):
    """
    ورشة عمل
    
    يستخدمها السكرتير لضمان الكفاءة.
    """
    
    __tablename__ = 'workshops'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # عنوان الورشة
    description = db.Column(db.Text)  # وصف الورشة
    objectives = db.Column(db.Text)  # أهداف الورشة
    
    # الموعد والمكان
    scheduled_date = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Float, default=2.0)  # المدة بالساعات
    location = db.Column(db.String(200))  # المكان
    
    # المجموعة المستهدفة
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    target_audience = db.Column(db.String(200))  # الجمهور المستهدف
    max_participants = db.Column(db.Integer, default=20)
    
    # الحالة
    is_completed = db.Column(db.Boolean, default=False)
    attendance_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)  # ملاحظات بعد الانتهاء
    
    # المنشئ
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', backref='workshops')
    
    def __repr__(self) -> str:
        return f'<Workshop {self.title}>'


class Template(db.Model):
    """
    نموذج للتنفيذ
    
    يستخدمها السكرتير لإصدار نماذج للمجموعات.
    """
    
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # عنوان النموذج
    description = db.Column(db.Text)  # وصف النموذج
    category = db.Column(db.String(50))  # التصنيف
    
    # محتوى النموذج
    content = db.Column(db.Text)  # محتوى النموذج (يمكن أن يكون HTML أو Markdown)
    file_path = db.Column(db.String(500), nullable=True)  # مسار الملف المرفق
    
    # الإصدار
    version = db.Column(db.String(20), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    
    # المجموعة المرتبطة (اختياري)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # المنشئ
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', backref='templates')
    
    def __repr__(self) -> str:
        return f'<Template {self.title} v{self.version}>'


class DirectiveStatus(str, Enum):
    """حالة التوجيه"""
    PENDING = 'pending'        # قيد الانتظار
    IN_PROGRESS = 'in_progress'  # قيد التنفيذ
    COMPLETED = 'completed'    # مكتمل
    CANCELLED = 'cancelled'    # ملغي


class Directive(db.Model):
    """
    توجيه من المدير
    
    يتابعه السكرتير وينفذه نائب المدير.
    """
    
    __tablename__ = 'directives'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)  # عنوان التوجيه
    description = db.Column(db.Text, nullable=False)  # وصف التوجيه
    priority = db.Column(db.String(20), default='normal')  # الأولوية: low, normal, high, urgent
    
    # الحالة
    status = db.Column(db.String(20), default=DirectiveStatus.PENDING.value)
    progress_notes = db.Column(db.Text)  # ملاحظات التقدم
    
    # التواريخ
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)  # تاريخ الاستحقاق
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # المجموعة المستهدفة
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # المُصدر (المدير) والمنفذ (نائب المدير)
    issued_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    issuer = db.relationship('User', foreign_keys=[issued_by], backref='issued_directives')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_directives')
    department = db.relationship('Department', backref='directives')
    
    def __repr__(self) -> str:
        return f'<Directive {self.title}>'
    
    def mark_in_progress(self):
        """تحديد التوجيه كقيد التنفيذ"""
        self.status = DirectiveStatus.IN_PROGRESS.value
        db.session.commit()
    
    def mark_completed(self):
        """تحديد التوجيه كمكتمل"""
        self.status = DirectiveStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        db.session.commit()


class AlertType(str, Enum):
    """نوع التنبيه"""
    INFO = 'info'          # معلومات
    WARNING = 'warning'    # تحذير
    SUCCESS = 'success'    # نجاح
    DANGER = 'danger'      # خطر


class Alert(db.Model):
    """
    تنبيه للمدير
    
    يظهر في شاشة المدير للأمور المهمة.
    """
    
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # عنوان التنبيه
    message = db.Column(db.Text, nullable=False)  # رسالة التنبيه
    alert_type = db.Column(db.String(20), default=AlertType.INFO.value)  # نوع التنبيه
    
    # الرابط (اختياري) - للانتقال لمزيد من التفاصيل
    link = db.Column(db.String(500), nullable=True)
    
    # الحالة
    is_read = db.Column(db.Boolean, default=False)
    is_dismissed = db.Column(db.Boolean, default=False)
    
    # المجموعة المرتبطة (اختياري)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # المُرسل والمُستلم
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    target_role = db.Column(db.String(20), nullable=True)  # الدور المستهدف (مثل DIRECTOR)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # تاريخ انتهاء الصلاحية
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', backref='alerts')
    
    def __repr__(self) -> str:
        return f'<Alert {self.title}>'
    
    @classmethod
    def get_unread_for_director(cls) -> List['Alert']:
        """جلب التنبيهات غير المقروءة للمدير"""
        return cls.query.filter(
            cls.is_read == False,
            cls.is_dismissed == False,
            (cls.target_role == 'DIRECTOR') | (cls.target_role == None),
            (cls.expires_at == None) | (cls.expires_at > datetime.utcnow())
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def create_alert(cls, title: str, message: str, alert_type: str = 'info',
                     department_id: int = None, created_by: str = None,
                     target_role: str = 'DIRECTOR', link: str = None) -> 'Alert':
        """إنشاء تنبيه جديد"""
        alert = cls(
            title=title,
            message=message,
            alert_type=alert_type,
            department_id=department_id,
            created_by=created_by,
            target_role=target_role,
            link=link
        )
        db.session.add(alert)
        db.session.commit()
        return alert


# KPI Model for Director Dashboard
class KPI(db.Model):
    """
    مؤشر أداء رئيسي
    
    يظهر في شاشة المدير.
    """
    
    __tablename__ = 'kpis'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # اسم المؤشر
    description = db.Column(db.Text)  # وصف المؤشر
    
    # القيم
    target_value = db.Column(db.Float, nullable=False)  # القيمة المستهدفة
    current_value = db.Column(db.Float, default=0.0)  # القيمة الحالية
    unit = db.Column(db.String(20), default='%')  # الوحدة (%, عدد، الخ)
    
    # العرض
    icon = db.Column(db.String(50), default='bi-graph-up')
    color = db.Column(db.String(7), default='#0d6efd')
    order_index = db.Column(db.Integer, default=0)
    
    # المجموعة المرتبطة (اختياري)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # الفترة
    period_type = db.Column(db.String(20), default='yearly')  # monthly, quarterly, yearly
    year = db.Column(db.Integer, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', backref='kpis')
    
    def __repr__(self) -> str:
        return f'<KPI {self.name}: {self.current_value}/{self.target_value}>'
    
    @property
    def progress_percentage(self) -> float:
        """حساب نسبة التقدم"""
        if self.target_value == 0:
            return 0.0
        return min((self.current_value / self.target_value) * 100, 100)
    
    @classmethod
    def get_active_kpis(cls, year: int = None) -> List['KPI']:
        """جلب مؤشرات الأداء النشطة"""
        query = cls.query.filter_by(is_active=True)
        if year:
            query = query.filter_by(year=year)
        return query.order_by(cls.order_index).all()
