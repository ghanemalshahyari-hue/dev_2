"""
User Department Permissions Model

صلاحيات المستخدم على المجموعات (الأقسام).
يسمح بمنح صلاحيات إضافية للمستخدمين على مجموعات غير مجموعتهم.

مثال: مدير المجموعة يمكن منحه صلاحية:
- قراءة فقط (READ) على مجموعات أخرى
- قراءة وتعديل (WRITE) على مجموعات أخرى
"""

from datetime import datetime
from enum import Enum
from app.extensions import db


class PermissionType(Enum):
    """أنواع الصلاحيات على المجموعات."""
    NONE = 'none'           # لا صلاحية
    READ = 'read'           # قراءة فقط - عرض البيانات
    WRITE = 'write'         # قراءة وتعديل - تعديل البيانات
    FULL = 'full'           # صلاحية كاملة - تعديل + حذف + إدارة


class UserDepartmentPermission(db.Model):
    """
    صلاحيات إضافية للمستخدم على المجموعات.
    
    يستخدم لمنح مدراء المجموعات صلاحيات على مجموعات أخرى
    غير مجموعتهم الأصلية.
    
    Attributes:
        id: المعرف
        user_id: معرف المستخدم
        department_id: معرف المجموعة
        permission_type: نوع الصلاحية (قراءة/تعديل/كاملة)
        granted_by_id: من منح هذه الصلاحية
        notes: ملاحظات
        is_active: هل الصلاحية فعالة
        expires_at: تاريخ انتهاء الصلاحية (اختياري)
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    
    __tablename__ = 'user_department_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    permission_type = db.Column(db.Enum(PermissionType), default=PermissionType.READ, nullable=False)
    
    # من منح هذه الصلاحية
    granted_by_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # الحالة
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # تاريخ انتهاء الصلاحية
    
    # التواريخ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='extra_permissions')
    department = db.relationship('Department', backref='user_permissions')
    granted_by = db.relationship('User', foreign_keys=[granted_by_id])
    
    # Unique constraint - كل مستخدم له صلاحية واحدة فقط على كل مجموعة
    __table_args__ = (
        db.UniqueConstraint('user_id', 'department_id', name='uq_user_department_permission'),
    )
    
    def __repr__(self) -> str:
        return f'<UserDepartmentPermission user={self.user_id} dept={self.department_id} type={self.permission_type.value}>'
    
    @property
    def is_valid(self) -> bool:
        """التحقق من أن الصلاحية فعالة وغير منتهية."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    @property
    def can_read(self) -> bool:
        """هل يمكنه القراءة."""
        return self.is_valid and self.permission_type != PermissionType.NONE
    
    @property
    def can_write(self) -> bool:
        """هل يمكنه التعديل."""
        return self.is_valid and self.permission_type in [PermissionType.WRITE, PermissionType.FULL]
    
    @property
    def has_full_access(self) -> bool:
        """هل لديه صلاحية كاملة."""
        return self.is_valid and self.permission_type == PermissionType.FULL
    
    @classmethod
    def get_user_permissions(cls, user_id: str) -> list:
        """الحصول على جميع صلاحيات المستخدم الإضافية."""
        return cls.query.filter_by(user_id=user_id, is_active=True).all()
    
    @classmethod
    def get_user_departments(cls, user_id: str) -> list:
        """الحصول على معرفات المجموعات التي لدى المستخدم صلاحية عليها."""
        permissions = cls.query.filter_by(user_id=user_id, is_active=True).all()
        return [p.department_id for p in permissions if p.is_valid]
    
    @classmethod
    def check_permission(cls, user_id: str, department_id: int) -> 'UserDepartmentPermission':
        """التحقق من صلاحية المستخدم على مجموعة معينة."""
        permission = cls.query.filter_by(
            user_id=user_id,
            department_id=department_id,
            is_active=True
        ).first()
        return permission if permission and permission.is_valid else None
    
    @classmethod
    def can_user_read(cls, user_id: str, department_id: int) -> bool:
        """التحقق من إمكانية القراءة."""
        permission = cls.check_permission(user_id, department_id)
        return permission is not None and permission.can_read
    
    @classmethod
    def can_user_write(cls, user_id: str, department_id: int) -> bool:
        """التحقق من إمكانية التعديل."""
        permission = cls.check_permission(user_id, department_id)
        return permission is not None and permission.can_write
    
    @classmethod
    def grant_permission(cls, user_id: str, department_id: int, 
                        permission_type: PermissionType, 
                        granted_by_id: str = None, notes: str = None,
                        expires_at: datetime = None) -> 'UserDepartmentPermission':
        """منح صلاحية لمستخدم على مجموعة."""
        # التحقق من وجود صلاحية سابقة
        existing = cls.query.filter_by(user_id=user_id, department_id=department_id).first()
        
        if existing:
            # تحديث الصلاحية الموجودة
            existing.permission_type = permission_type
            existing.granted_by_id = granted_by_id
            existing.notes = notes
            existing.is_active = True
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
            permission = existing
        else:
            # إنشاء صلاحية جديدة
            permission = cls(
                user_id=user_id,
                department_id=department_id,
                permission_type=permission_type,
                granted_by_id=granted_by_id,
                notes=notes,
                expires_at=expires_at
            )
            db.session.add(permission)
        
        db.session.commit()
        return permission
    
    @classmethod
    def revoke_permission(cls, user_id: str, department_id: int) -> bool:
        """إلغاء صلاحية من مستخدم."""
        permission = cls.query.filter_by(user_id=user_id, department_id=department_id).first()
        if permission:
            permission.is_active = False
            db.session.commit()
            return True
        return False
    
    @classmethod
    def get_department_users(cls, department_id: int) -> list:
        """الحصول على المستخدمين الذين لديهم صلاحيات على مجموعة معينة."""
        return cls.query.filter_by(department_id=department_id, is_active=True).all()
