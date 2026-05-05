from app import create_app
from app.extensions import db
from app.models.department import Department

app = create_app()

with app.app_context():
    # حذف جميع المجموعات
    db.session.query(Department).delete()
    db.session.commit()

    # إنشاء 5 مجموعات
    departments = [
        {
            'code': 'GRP1',
            'name': 'الفهوم العملياتي المشرك رقم 2',
            'description': '',
            'color': '#FF6384',
            'icon': 'bi-1-circle-fill',
            'order_index': 1,
            'is_visible': True,
            'is_active': True
        },
        *[
            {
                'code': f'GRP{i}',
                'name': '',
                'description': '',
                'color': '#FF6384',
                'icon': f'bi-{i}-circle-fill',
                'order_index': i,
                'is_visible': True,
                'is_active': True
            } for i in range(2, 6)
        ]
    ]
    for dept in departments:
        db.session.add(Department(**dept))
    db.session.commit()

print('تم حذف وإنشاء المجموعات بنجاح!')
