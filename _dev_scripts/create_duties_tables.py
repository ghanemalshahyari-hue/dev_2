"""
سكريبت إنشاء جداول الواجبات والمشاريع

يقوم بـ:
1. إنشاء الجداول الجديدة
2. إضافة بيانات تجريبية للمجموعة الأولى
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    Department, User,
    Entity, Duty, DutyStatus,
    Objective, Project, Activity, ActivityStatus,
    ActivityOutput, Deliverable, CompletionMethod
)


def create_tables():
    """إنشاء الجداول الجديدة"""
    print("جاري إنشاء الجداول...")
    db.create_all()
    print("✓ تم إنشاء الجداول بنجاح")


def create_sample_data():
    """إنشاء بيانات تجريبية للعرض"""
    
    # الحصول على المجموعة الأولى
    dept1 = Department.query.filter_by(code='GRP1').first()
    if not dept1:
        print("✗ لم يتم العثور على المجموعة الأولى")
        return
    
    # الحصول على مستخدم للإنشاء
    creator = User.query.filter_by(username='director').first()
    if not creator:
        creator = User.query.first()
    
    if not creator:
        print("✗ لم يتم العثور على مستخدم")
        return
    
    print(f"جاري إنشاء البيانات التجريبية للمجموعة: {dept1.name}")
    
    # ========== إنشاء الجهات ==========
    entities_data = [
        {'code': 'E1-1', 'name': 'الجهة الأولى', 'description': 'الجهة المسؤولة عن الواجبات التشغيلية'},
        {'code': 'E1-2', 'name': 'الجهة الثانية', 'description': 'الجهة المسؤولة عن الواجبات الإدارية'},
        {'code': 'E1-3', 'name': 'الجهة الثالثة', 'description': 'الجهة المسؤولة عن الواجبات الفنية'},
    ]
    
    entities = []
    for i, e_data in enumerate(entities_data):
        entity = Entity.query.filter_by(code=e_data['code'], department_id=dept1.id).first()
        if not entity:
            entity = Entity(
                department_id=dept1.id,
                code=e_data['code'],
                name=e_data['name'],
                description=e_data['description'],
                order_index=i
            )
            db.session.add(entity)
            db.session.flush()
        entities.append(entity)
    
    print(f"✓ تم إنشاء {len(entities)} جهات")
    
    # ========== إنشاء الواجبات ==========
    duties_data = [
        {
            'duty_number': '1.15',
            'title': 'تطوير البنية التحتية التقنية',
            'description': 'واجب يتضمن تطوير وتحديث البنية التحتية التقنية للمنظومة',
            'entity_index': 0,
            'priority': 3,
            'objectives': [
                {
                    'number': '1.15.1',
                    'title': 'تحديث الأنظمة القديمة',
                    'description': 'استبدال الأنظمة القديمة بأنظمة حديثة',
                    'projects': [
                        {
                            'number': '1',
                            'title': 'مشروع تحديث السيرفرات',
                            'description': 'ترقية السيرفرات إلى أحدث المواصفات',
                            'activities': [
                                {'number': '1.1', 'title': 'دراسة الوضع الحالي', 'duration': 30, 'completion': 100},
                                {'number': '1.2', 'title': 'تحديد المتطلبات', 'duration': 45, 'completion': 85},
                                {'number': '1.3', 'title': 'شراء المعدات', 'duration': 60, 'completion': 50},
                                {'number': '1.4', 'title': 'التركيب والتشغيل', 'duration': 90, 'completion': 0},
                            ]
                        },
                        {
                            'number': '2',
                            'title': 'مشروع تطوير الشبكات',
                            'description': 'تحسين البنية الشبكية',
                            'activities': [
                                {'number': '2.1', 'title': 'تقييم الشبكة الحالية', 'duration': 20, 'completion': 100},
                                {'number': '2.2', 'title': 'تصميم الشبكة الجديدة', 'duration': 40, 'completion': 60},
                                {'number': '2.3', 'title': 'التنفيذ', 'duration': 120, 'completion': 0},
                            ]
                        }
                    ]
                }
            ]
        },
        {
            'duty_number': '1.11',
            'title': 'تأهيل الكوادر البشرية',
            'description': 'برنامج شامل لتأهيل وتدريب الموظفين',
            'entity_index': 1,
            'priority': 2,
            'objectives': [
                {
                    'number': '1.11.1',
                    'title': 'برنامج التدريب الأساسي',
                    'description': 'تدريب جميع الموظفين على المهارات الأساسية',
                    'projects': [
                        {
                            'number': '1',
                            'title': 'ورش العمل التأهيلية',
                            'description': 'سلسلة من ورش العمل للتأهيل',
                            'activities': [
                                {'number': '1.1', 'title': 'إعداد المحتوى التدريبي', 'duration': 40, 'completion': 100},
                                {'number': '1.2', 'title': 'تنفيذ الورشة الأولى', 'duration': 7, 'completion': 100},
                                {'number': '1.3', 'title': 'تنفيذ الورشة الثانية', 'duration': 7, 'completion': 75},
                                {'number': '1.4', 'title': 'تقييم النتائج', 'duration': 14, 'completion': 0},
                            ]
                        }
                    ]
                }
            ]
        },
        {
            'duty_number': '1.10',
            'title': 'تحسين العمليات التشغيلية',
            'description': 'مراجعة وتحسين جميع العمليات التشغيلية',
            'entity_index': 2,
            'priority': 1,
            'objectives': [
                {
                    'number': '1.10.1',
                    'title': 'توثيق العمليات الحالية',
                    'description': 'توثيق جميع العمليات التشغيلية الحالية',
                    'projects': [
                        {
                            'number': '1',
                            'title': 'مشروع التوثيق',
                            'description': 'توثيق شامل للعمليات',
                            'activities': [
                                {'number': '1.1', 'title': 'جمع المعلومات', 'duration': 60, 'completion': 90},
                                {'number': '1.2', 'title': 'تحليل العمليات', 'duration': 45, 'completion': 70},
                                {'number': '1.3', 'title': 'كتابة التوثيق', 'duration': 90, 'completion': 30},
                                {'number': '1.4', 'title': 'المراجعة والتدقيق', 'duration': 30, 'completion': 0},
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    
    today = date.today()
    year_start = date(today.year, 1, 1)
    
    for duty_data in duties_data:
        # التحقق من عدم وجود الواجب
        existing_duty = Duty.query.filter_by(
            duty_number=duty_data['duty_number'],
            department_id=dept1.id
        ).first()
        
        if existing_duty:
            print(f"  - الواجب {duty_data['duty_number']} موجود مسبقاً")
            continue
        
        # إنشاء الواجب
        duty = Duty(
            department_id=dept1.id,
            entity_id=entities[duty_data['entity_index']].id,
            duty_number=duty_data['duty_number'],
            title=duty_data['title'],
            description=duty_data['description'],
            priority=duty_data['priority'],
            status=DutyStatus.IN_PROGRESS.value,
            start_year=today.year,
            end_year=today.year + 5,
            created_by=creator.id
        )
        db.session.add(duty)
        db.session.flush()
        
        print(f"  + الواجب: {duty.duty_number} - {duty.title}")
        
        # إنشاء الأهداف
        for obj_data in duty_data['objectives']:
            objective = Objective(
                duty_id=duty.id,
                objective_number=obj_data['number'],
                title=obj_data['title'],
                description=obj_data['description'],
                start_date=year_start,
                end_date=year_start + timedelta(days=365*5)
            )
            db.session.add(objective)
            db.session.flush()
            
            print(f"    + الهدف: {objective.objective_number}")
            
            # إنشاء المشاريع
            activity_start = year_start
            for proj_data in obj_data['projects']:
                project = Project(
                    objective_id=objective.id,
                    project_number=proj_data['number'],
                    title=proj_data['title'],
                    description=proj_data['description'],
                    start_date=activity_start,
                    completion_method=CompletionMethod.AUTO_ACTIVITIES.value
                )
                db.session.add(project)
                db.session.flush()
                
                print(f"      + المشروع: {project.project_number} - {project.title}")
                
                # إنشاء الأنشطة
                for act_data in proj_data['activities']:
                    act_end = activity_start + timedelta(days=act_data['duration'])
                    
                    activity = Activity(
                        project_id=project.id,
                        activity_number=act_data['number'],
                        title=act_data['title'],
                        start_date=activity_start,
                        end_date=act_end,
                        completion_percentage=act_data['completion'],
                        status=ActivityStatus.COMPLETED.value if act_data['completion'] >= 100 else (
                            ActivityStatus.IN_PROGRESS.value if act_data['completion'] > 0 else ActivityStatus.NOT_STARTED.value
                        ),
                        data_filled=act_data['completion'] > 0
                    )
                    db.session.add(activity)
                    
                    print(f"        + النشاط: {activity.activity_number} ({activity.completion_percentage}%)")
                    
                    activity_start = act_end
                
                # تحديث تاريخ نهاية المشروع
                project.end_date = activity_start
    
    db.session.commit()
    print("\n✓ تم إنشاء البيانات التجريبية بنجاح!")


def main():
    """الدالة الرئيسية"""
    app = create_app()
    
    with app.app_context():
        create_tables()
        
        # التحقق من وجود بيانات
        existing = Duty.query.count()
        if existing > 0:
            print(f"\nتوجد {existing} واجبات مسبقاً.")
            response = input("هل تريد إضافة بيانات تجريبية جديدة؟ (y/n): ")
            if response.lower() != 'y':
                print("تم الإلغاء.")
                return
        
        create_sample_data()
        
        # عرض ملخص
        print("\n" + "="*50)
        print("ملخص البيانات:")
        print(f"  - الجهات: {Entity.query.count()}")
        print(f"  - الواجبات: {Duty.query.count()}")
        print(f"  - الأهداف: {Objective.query.count()}")
        print(f"  - المشاريع: {Project.query.count()}")
        print(f"  - الأنشطة: {Activity.query.count()}")
        print("="*50)


if __name__ == '__main__':
    main()
