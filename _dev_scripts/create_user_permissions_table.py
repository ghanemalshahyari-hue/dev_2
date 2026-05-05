"""
سكربت إنشاء جدول صلاحيات المستخدمين على المجموعات.

يُنشئ جدول user_department_permissions للسماح بمنح صلاحيات
إضافية لمدراء المجموعات على مجموعات أخرى.
"""

import sys
import os

# إضافة مسار التطبيق
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user_permissions import UserDepartmentPermission, PermissionType


def create_permissions_table():
    """إنشاء جدول الصلاحيات."""
    app = create_app()
    
    with app.app_context():
        # إنشاء الجدول إذا لم يكن موجوداً
        db.create_all()
        print("✅ تم إنشاء جدول user_department_permissions بنجاح!")
        
        # عرض معلومات الجدول
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if 'user_department_permissions' in inspector.get_table_names():
            columns = inspector.get_columns('user_department_permissions')
            print("\n📋 أعمدة الجدول:")
            for col in columns:
                print(f"   - {col['name']}: {col['type']}")
        
        print("\n📖 أنواع الصلاحيات المتاحة:")
        for ptype in PermissionType:
            print(f"   - {ptype.value}: {ptype.name}")
        
        print("\n" + "="*50)
        print("✨ الاستخدام:")
        print("="*50)
        print("""
# منح صلاحية قراءة لمستخدم على مجموعة:
from app.models.user_permissions import UserDepartmentPermission, PermissionType
UserDepartmentPermission.grant_permission(
    user_id='user-uuid',
    department_id=2,
    permission_type=PermissionType.READ,
    granted_by_id='admin-uuid',
    notes='صلاحية عرض مجموعة التخطيط'
)

# منح صلاحية كتابة:
UserDepartmentPermission.grant_permission(
    user_id='user-uuid',
    department_id=3,
    permission_type=PermissionType.WRITE
)

# إلغاء صلاحية:
UserDepartmentPermission.revoke_permission(
    user_id='user-uuid',
    department_id=2
)

# التحقق من صلاحية:
can_read = UserDepartmentPermission.can_user_read('user-uuid', 2)
can_write = UserDepartmentPermission.can_user_write('user-uuid', 2)
""")


def add_sample_permissions():
    """إضافة صلاحيات تجريبية (اختياري)."""
    app = create_app()
    
    with app.app_context():
        from app.models.user import User
        from app.models.department import Department
        
        # البحث عن مستخدم مدير مجموعة
        from app.models.role import PERMISSIONS
        group_admin = User.query.filter(
            User.is_active == True
        ).first()
        
        if not group_admin:
            print("⚠️ لم يتم العثور على مستخدمين")
            return
        
        # البحث عن مجموعة أخرى غير مجموعة المستخدم
        other_dept = Department.query.filter(
            Department.id != group_admin.department_id,
            Department.is_active == True
        ).first()
        
        if not other_dept:
            print("⚠️ لم يتم العثور على مجموعات أخرى")
            return
        
        # منح صلاحية قراءة
        permission = UserDepartmentPermission.grant_permission(
            user_id=group_admin.id,
            department_id=other_dept.id,
            permission_type=PermissionType.READ,
            notes='صلاحية تجريبية للعرض'
        )
        
        print(f"✅ تم منح صلاحية قراءة للمستخدم: {group_admin.full_name}")
        print(f"   على المجموعة: {other_dept.name}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='إنشاء جدول صلاحيات المستخدمين')
    parser.add_argument('--sample', action='store_true', help='إضافة صلاحيات تجريبية')
    
    args = parser.parse_args()
    
    create_permissions_table()
    
    if args.sample:
        print("\n" + "="*50)
        print("🔧 إضافة صلاحيات تجريبية...")
        print("="*50)
        add_sample_permissions()
