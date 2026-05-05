"""
Duties, Projects & Activities Models - نماذج الواجبات والمشاريع والأنشطة

الهيكل الهرمي:
المجموعة (Department)
    └── الواجب الرئيسي (Duty) - مثل 1.15, 1.11
        └── الجهة المسؤولة (Entity)
            └── الهدف الأساسي (Objective)
                └── المشروع (Project)
                    └── النشاط (Activity)

هذا النظام يسمح بـ:
- تتبع الواجبات الرئيسية لكل مجموعة
- ربط كل واجب بجهة مسؤولة
- تقسيم الأهداف إلى مشاريع ثم أنشطة
- حساب نسب الإنجاز والاستكمال تلقائياً
- تتبع الجدول الزمني على 5 سنوات
"""

from datetime import datetime, date
from typing import List, Optional
from enum import Enum

from app.extensions import db


class DutyStatus(str, Enum):
    """حالة الواجب"""
    PLANNING = 'planning'      # قيد التخطيط
    IN_PROGRESS = 'in_progress'  # قيد التنفيذ
    ON_HOLD = 'on_hold'        # معلق
    COMPLETED = 'completed'    # مكتمل
    CANCELLED = 'cancelled'    # ملغي


class ActivityStatus(str, Enum):
    """حالة النشاط"""
    NOT_STARTED = 'not_started'  # لم يبدأ
    IN_PROGRESS = 'in_progress'  # قيد التنفيذ
    DELAYED = 'delayed'          # متأخر
    COMPLETED = 'completed'      # مكتمل
    CANCELLED = 'cancelled'      # ملغي


class CompletionMethod(str, Enum):
    """طريقة حساب الاستكمال"""
    DATA_ENTRY = 'data_entry'      # بناءً على إدخال البيانات
    MANUAL = 'manual'              # يدوي
    AUTO_ACTIVITIES = 'auto_activities'  # تلقائي من الأنشطة
    DELIVERABLES = 'deliverables'  # بناءً على المخرجات


# ========== الجهة (Entity) ==========
class Entity(db.Model):
    """
    الجهة داخل المجموعة
    
    كل مجموعة لديها عدة جهات، وكل جهة مسؤولة عن واجبات معينة.
    """
    
    __tablename__ = 'entities'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    code = db.Column(db.String(20), nullable=False)  # رمز الجهة مثل "E1-1"
    name = db.Column(db.String(150), nullable=False)  # اسم الجهة
    description = db.Column(db.Text)  # وصف الجهة
    
    manager_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', backref=db.backref('entities', lazy='dynamic'))
    manager = db.relationship('User', foreign_keys=[manager_id])
    duties = db.relationship('Duty', back_populates='entity', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'code', name='unique_entity_code_per_dept'),
    )
    
    def __repr__(self) -> str:
        return f'<Entity {self.code}: {self.name}>'
    
    def get_completion_percentage(self) -> float:
        """حساب نسبة الإنجاز الكلية للجهة"""
        duties = self.duties.filter_by(is_active=True).all()
        if not duties:
            return 0.0
        
        total = sum(d.get_completion_percentage() for d in duties)
        return total / len(duties)


# ========== الواجب الرئيسي (Duty) ==========
class Duty(db.Model):
    """
    الواجب الرئيسي
    
    مثل: الواجب رقم 1.15، 1.11، 1.10
    كل واجب مرتبط بمجموعة وجهة مسؤولة.
    """
    
    __tablename__ = 'duties'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=True)
    
    # ترقيم الواجب
    duty_number = db.Column(db.String(20), nullable=False)  # مثل "1.15"
    title = db.Column(db.String(300), nullable=False)  # عنوان الواجب
    description = db.Column(db.Text)  # وصف تفصيلي
    
    # التصنيف والأولوية
    priority = db.Column(db.Integer, default=1)  # 1=عادي, 2=مهم, 3=عاجل
    status = db.Column(db.String(20), default=DutyStatus.PLANNING.value)
    
    # الجدول الزمني
    start_year = db.Column(db.Integer, nullable=True)  # سنة البداية
    end_year = db.Column(db.Integer, nullable=True)    # سنة النهاية (افتراضي 5 سنوات)
    
    # طريقة حساب الاستكمال
    completion_method = db.Column(db.String(30), default=CompletionMethod.AUTO_ACTIVITIES.value)
    manual_completion = db.Column(db.Float, default=0.0)  # النسبة اليدوية إذا كانت الطريقة يدوية
    
    # البيانات الوصفية
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    # Relationships
    department = db.relationship('Department', backref=db.backref('duties', lazy='dynamic'))
    entity = db.relationship('Entity', back_populates='duties')
    creator = db.relationship('User', foreign_keys=[created_by])
    objectives = db.relationship('Objective', back_populates='duty', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'duty_number', name='unique_duty_number_per_dept'),
    )
    
    def __repr__(self) -> str:
        return f'<Duty {self.duty_number}: {self.title}>'
    
    def get_completion_percentage(self) -> float:
        """حساب نسبة الإنجاز"""
        if self.completion_method == CompletionMethod.MANUAL.value:
            return self.manual_completion
        
        objectives = self.objectives.filter_by(is_active=True).all()
        if not objectives:
            return 0.0
        
        total = sum(obj.get_completion_percentage() for obj in objectives)
        return total / len(objectives)
    
    def get_status_display(self) -> str:
        """الحصول على نص الحالة"""
        status_map = {
            'planning': 'قيد التخطيط',
            'in_progress': 'قيد التنفيذ',
            'on_hold': 'معلق',
            'completed': 'مكتمل',
            'cancelled': 'ملغي'
        }
        return status_map.get(self.status, self.status)


# ========== الهدف الأساسي (Objective) ==========
class Objective(db.Model):
    """
    الهدف الأساسي للواجب
    
    كل واجب له هدف أساسي واحد أو أكثر.
    الهدف يقسم إلى مشاريع متعددة.
    """
    
    __tablename__ = 'objectives'
    
    id = db.Column(db.Integer, primary_key=True)
    duty_id = db.Column(db.Integer, db.ForeignKey('duties.id'), nullable=False)
    
    # ترقيم الهدف
    objective_number = db.Column(db.String(20), nullable=False)  # مثل "1.15.1"
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    
    # المؤشرات والقياس
    target_indicator = db.Column(db.String(200))  # مؤشر الأداء
    target_value = db.Column(db.Float, nullable=True)  # القيمة المستهدفة
    current_value = db.Column(db.Float, default=0.0)  # القيمة الحالية
    
    # الجدول الزمني
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    duty = db.relationship('Duty', back_populates='objectives')
    projects = db.relationship('Project', back_populates='objective', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self) -> str:
        return f'<Objective {self.objective_number}: {self.title}>'
    
    def get_completion_percentage(self) -> float:
        """حساب نسبة الإنجاز من المشاريع"""
        projects = self.projects.filter_by(is_active=True).all()
        if not projects:
            # إذا لم يكن هناك مشاريع، نحسب من target_value
            if self.target_value and self.target_value > 0:
                return min((self.current_value / self.target_value) * 100, 100)
            return 0.0
        
        total = sum(p.get_completion_percentage() for p in projects)
        return total / len(projects)


# ========== المشروع (Project) ==========
class Project(db.Model):
    """
    المشروع
    
    كل هدف يقسم إلى مشاريع متعددة.
    كل مشروع له أنشطة ومخرجات.
    """
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    objective_id = db.Column(db.Integer, db.ForeignKey('objectives.id'), nullable=False)
    
    # ترقيم المشروع
    project_number = db.Column(db.String(20), nullable=False)  # مثل "1"
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)  # شرح المشروع
    
    # الجدول الزمني
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    
    # الميزانية (اختياري)
    budget = db.Column(db.Float, nullable=True)
    actual_cost = db.Column(db.Float, default=0.0)
    
    # المسؤول
    manager_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    # طريقة حساب الاستكمال
    completion_method = db.Column(db.String(30), default=CompletionMethod.AUTO_ACTIVITIES.value)
    manual_completion = db.Column(db.Float, default=0.0)
    
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    objective = db.relationship('Objective', back_populates='projects')
    manager = db.relationship('User', foreign_keys=[manager_id])
    activities = db.relationship('Activity', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    deliverables = db.relationship('Deliverable', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self) -> str:
        return f'<Project {self.project_number}: {self.title}>'
    
    def get_completion_percentage(self) -> float:
        """حساب نسبة الإنجاز"""
        if self.completion_method == CompletionMethod.MANUAL.value:
            return self.manual_completion
        
        if self.completion_method == CompletionMethod.DELIVERABLES.value:
            deliverables = self.deliverables.all()
            if not deliverables:
                return 0.0
            completed = sum(1 for d in deliverables if d.is_completed)
            return (completed / len(deliverables)) * 100
        
        # حساب من الأنشطة
        activities = self.activities.filter_by(is_active=True).all()
        if not activities:
            return 0.0
        
        total = sum(a.completion_percentage for a in activities)
        return total / len(activities)
    
    def get_days_remaining(self) -> Optional[int]:
        """حساب الأيام المتبقية"""
        if not self.end_date:
            return None
        
        delta = self.end_date - date.today()
        return delta.days
    
    def is_overdue(self) -> bool:
        """هل المشروع متأخر؟"""
        days = self.get_days_remaining()
        return days is not None and days < 0


# ========== النشاط (Activity) ==========
class Activity(db.Model):
    """
    النشاط
    
    أصغر وحدة في الهيكل.
    كل نشاط له تاريخ بداية ونهاية ونسبة إنجاز.
    """
    
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # ترقيم النشاط
    activity_number = db.Column(db.String(20), nullable=False)  # مثل "1.1", "1.2"
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    
    # الجدول الزمني (ضمن 5 سنوات)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    actual_start = db.Column(db.Date, nullable=True)  # تاريخ البداية الفعلي
    actual_end = db.Column(db.Date, nullable=True)    # تاريخ النهاية الفعلي
    
    # نسبة الإنجاز
    completion_percentage = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default=ActivityStatus.NOT_STARTED.value)
    
    # المسؤول المباشر
    assignee_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    # بيانات إضافية
    notes = db.Column(db.Text)  # ملاحظات
    data_filled = db.Column(db.Boolean, default=False)  # هل تم تعبئة البيانات؟
    
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='activities')
    assignee = db.relationship('User', foreign_keys=[assignee_id])
    outputs = db.relationship('ActivityOutput', back_populates='activity', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self) -> str:
        return f'<Activity {self.activity_number}: {self.title}>'
    
    def get_status_display(self) -> str:
        """الحصول على نص الحالة"""
        status_map = {
            'not_started': 'لم يبدأ',
            'in_progress': 'قيد التنفيذ',
            'delayed': 'متأخر',
            'completed': 'مكتمل',
            'cancelled': 'ملغي'
        }
        return status_map.get(self.status, self.status)
    
    def update_status(self):
        """تحديث الحالة تلقائياً"""
        today = date.today()
        
        if self.completion_percentage >= 100:
            self.status = ActivityStatus.COMPLETED.value
        elif self.end_date and today > self.end_date and self.completion_percentage < 100:
            self.status = ActivityStatus.DELAYED.value
        elif self.completion_percentage > 0 or (self.start_date and today >= self.start_date):
            self.status = ActivityStatus.IN_PROGRESS.value
        else:
            self.status = ActivityStatus.NOT_STARTED.value
    
    def get_duration_days(self) -> Optional[int]:
        """حساب مدة النشاط بالأيام"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None
    
    def calculate_completion_from_data(self):
        """
        حساب نسبة الاستكمال بناءً على تعبئة البيانات
        
        إذا تم إضافة معلومات = نسبة أعلى
        إذا كان فارغاً = 0%
        """
        if not self.data_filled:
            if self.description or self.notes or self.outputs.count() > 0:
                self.data_filled = True
                self.completion_percentage = max(self.completion_percentage, 10.0)
        
        # حساب من المخرجات
        outputs = self.outputs.all()
        if outputs:
            completed_outputs = sum(1 for o in outputs if o.is_achieved)
            data_completion = (completed_outputs / len(outputs)) * 100
            self.completion_percentage = max(self.completion_percentage, data_completion)


# ========== مخرجات النشاط (Activity Output) ==========
class ActivityOutput(db.Model):
    """
    مخرجات النشاط
    
    ما هي المخرجات المتوقعة من كل نشاط؟
    """
    
    __tablename__ = 'activity_outputs'
    
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    
    title = db.Column(db.String(300), nullable=False)  # عنوان المخرج
    description = db.Column(db.Text)  # وصف المخرج
    
    expected_date = db.Column(db.Date, nullable=True)  # التاريخ المتوقع للتسليم
    actual_date = db.Column(db.Date, nullable=True)    # تاريخ التسليم الفعلي
    
    is_achieved = db.Column(db.Boolean, default=False)  # هل تم تحقيقه؟
    evidence = db.Column(db.Text)  # الدليل/المستندات
    file_path = db.Column(db.String(500), nullable=True)  # مسار الملف المرفق
    
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    activity = db.relationship('Activity', back_populates='outputs')
    
    def __repr__(self) -> str:
        return f'<ActivityOutput {self.title}>'


# ========== مخرجات المشروع (Deliverable) ==========
class Deliverable(db.Model):
    """
    مخرجات المشروع الرئيسية
    
    المخرجات الكبيرة على مستوى المشروع.
    """
    
    __tablename__ = 'deliverables'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    
    due_date = db.Column(db.Date, nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    
    is_completed = db.Column(db.Boolean, default=False)
    completion_percentage = db.Column(db.Float, default=0.0)
    
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', back_populates='deliverables')
    
    def __repr__(self) -> str:
        return f'<Deliverable {self.title}>'


# ========== Helper Functions ==========
def get_duty_full_hierarchy(duty_id: int) -> dict:
    """
    الحصول على الهيكل الكامل للواجب
    
    يعيد الواجب مع جميع الأهداف والمشاريع والأنشطة.
    """
    duty = Duty.query.get(duty_id)
    if not duty:
        return {}
    
    return {
        'duty': duty,
        'objectives': [
            {
                'objective': obj,
                'projects': [
                    {
                        'project': proj,
                        'activities': proj.activities.filter_by(is_active=True).order_by(Activity.order_index).all(),
                        'deliverables': proj.deliverables.order_by(Deliverable.order_index).all()
                    }
                    for proj in obj.projects.filter_by(is_active=True).order_by(Project.order_index).all()
                ]
            }
            for obj in duty.objectives.filter_by(is_active=True).order_by(Objective.order_index).all()
        ],
        'completion': duty.get_completion_percentage()
    }


def get_department_timeline(department_id: int, start_year: int, end_year: int) -> List[dict]:
    """
    الحصول على الجدول الزمني للمجموعة
    
    يعيد جميع الأنشطة مرتبة حسب التاريخ للعرض في Gantt Chart.
    """
    activities = []
    
    duties = Duty.query.filter_by(
        department_id=department_id,
        is_active=True
    ).all()
    
    for duty in duties:
        for obj in duty.objectives.filter_by(is_active=True).all():
            for proj in obj.projects.filter_by(is_active=True).all():
                for act in proj.activities.filter_by(is_active=True).all():
                    if act.start_date and act.end_date:
                        if act.start_date.year >= start_year and act.end_date.year <= end_year:
                            activities.append({
                                'duty': duty,
                                'objective': obj,
                                'project': proj,
                                'activity': act,
                                'start': act.start_date,
                                'end': act.end_date,
                                'completion': act.completion_percentage
                            })
    
    return sorted(activities, key=lambda x: x['start'])
