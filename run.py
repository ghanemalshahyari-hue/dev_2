"""
Development / Production Runner — Enterprise Dashboard v2.0

Usage:
    python run.py              # development (simulation mode)
    FLASK_ENV=production python run.py

On first run it creates the SQLite database and seeds:
  - 6 roles
  - 7 departments
  - 6 test user accounts (LDAP simulation)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _run_migrations(app):
    """Add any missing columns to existing tables (lightweight migration)."""
    from app.extensions import db
    from sqlalchemy import text, inspect

    with app.app_context():
        inspector = inspect(db.engine)
        
        # 1. departments table — add missing columns automatically
        if 'departments' in inspector.get_table_names():
            existing = {col['name'] for col in inspector.get_columns('departments')}
            # Map column name → DDL fragment for SQLite
            needed = {
                'is_central':         'BOOLEAN NOT NULL DEFAULT 0',
                'director_notes':     'TEXT DEFAULT ""',
                'concept_number':     'INTEGER',
                'responsible_person': 'VARCHAR(120) DEFAULT ""',
                'org_group_name':     'VARCHAR(160) DEFAULT ""',
            }
            with db.engine.connect() as conn:
                for col, ddl in needed.items():
                    if col not in existing:
                        conn.execute(text(
                            f'ALTER TABLE departments ADD COLUMN {col} {ddl}'
                        ))
                        conn.commit()
                        print(f'✓  Migration: added column departments.{col}')
                        
        # 2. main_tasks table - add missing JSON column automatically
        if 'main_tasks' in inspector.get_table_names():
            existing_mt = {col['name'] for col in inspector.get_columns('main_tasks')}
            needed_mt = {
                'secondary_departments_list': 'TEXT DEFAULT "[]"'
            }
            with db.engine.connect() as conn:
                for col, ddl in needed_mt.items():
                    if col not in existing_mt:
                        conn.execute(text(
                            f'ALTER TABLE main_tasks ADD COLUMN {col} {ddl}'
                        ))
                        conn.commit()
                        print(f'✓  Migration: added column main_tasks.{col}')


        # 3. agenda_items table - create it for existing databases
        if 'agenda_items' not in inspector.get_table_names():
            from app.models.agenda import AgendaItem
            AgendaItem.__table__.create(db.engine, checkfirst=True)
            print('Migration: created table agenda_items')
        else:
            existing_agenda = {col['name'] for col in inspector.get_columns('agenda_items')}
            needed_agenda = {
                'is_default': 'BOOLEAN NOT NULL DEFAULT 0',
                'event_key': 'VARCHAR(80)',
                'original_date': 'DATE',
            }
            with db.engine.connect() as conn:
                for col, ddl in needed_agenda.items():
                    if col not in existing_agenda:
                        conn.execute(text(
                            f'ALTER TABLE agenda_items ADD COLUMN {col} {ddl}'
                        ))
                        conn.commit()
                        print(f'Migration: added column agenda_items.{col}')


def init_database(app):
    """Create tables and seed default data.
    If the schema is stale (OperationalError), drop ALL tables and recreate.
    """
    from app.extensions import db
    from app.models.role import Role
    from app.models.department import Department
    from sqlalchemy.exc import OperationalError

    with app.app_context():
        # 1. Create missing tables
        db.create_all()
        # 2. Add any missing columns to existing tables
        _run_migrations(app)
        # 3. Seed roles
        try:
            Role.create_default_roles()
        except OperationalError:
            print('\n⚠  Stale database schema detected — resetting database …')
            db.drop_all()
            db.create_all()
            print('✓  Tables rebuilt.')
            Role.create_default_roles()

        Department.create_default_departments()

        if app.config.get('LDAP_SIMULATION_MODE'):
            _seed_test_users(app)

        print('\n✓ Database initialized successfully')


def _seed_test_users(app):
    """Create test users for LDAP simulation mode."""
    from app.extensions import db
    from app.models.user import User
    from app.models.role import Role
    from app.models.department import Department

    test_accounts = [
        ('dev',        'dev123',        'المطور / Developer',       'DEVELOPER',   None),
        ('director',   'director123',   'المدير العام',             'DIRECTOR',    None),
        ('secretary',  'secretary123',  'السكرتير',                 'SECRETARY',   None),
        ('deputy',     'deputy123',     'نائب المدير',               'DEPUTY',      None),
        ('groupadmin', 'groupadmin123', 'مدير المجموعة الأولى',     'GROUP_ADMIN', 'GRP1'),
        ('user',       'user123',       'مستخدم عادي',              'USER',        'GRP1'),
    ]

    first_dept = Department.query.first()

    for username, password, full_name, role_code, dept_code in test_accounts:
        if User.get_by_username(username):
            continue

        role = Role.get_by_code(role_code)
        if dept_code:
            dept = Department.query.filter_by(code=dept_code).first() or first_dept
        else:
            dept = None

        user = User(
            username       = username,
            email          = f'{username}@company.local',
            full_name      = full_name,
            ldap_dn        = f'CN={username},OU=Users,DC=company,DC=local',
            is_ldap_user   = True,
            role_id        = role.id if role else None,
            department_id  = dept.id if dept else None,
        )
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    print('✓ Test accounts seeded')


def _print_banner(config_name: str) -> None:
    print('\n' + '═' * 58)
    print('  🏢  Enterprise Dashboard v2.0')
    print(f'  ⚙   Config: {config_name}')
    print('═' * 58)
    print('\n  Test Accounts (LDAP Simulation):')
    print('  ┌──────────────┬──────────────────┬────────────────────┐')
    print('  │ Username     │ Password         │ Role               │')
    print('  ├──────────────┼──────────────────┼────────────────────┤')
    print('  │ dev          │ dev123           │ Developer (full)   │')
    print('  │ director     │ director123      │ المدير (CEO)       │')
    print('  │ secretary    │ secretary123     │ السكرتير           │')
    print('  │ deputy       │ deputy123        │ نائب المدير        │')
    print('  │ groupadmin   │ groupadmin123    │ مدير المجموعة      │')
    print('  │ user         │ user123          │ مستخدم             │')
    print('  └──────────────┴──────────────────┴────────────────────┘')
    print('\n  🌐  Open: http://127.0.0.1:5000')
    print('═' * 58 + '\n')


def main():
    from dotenv import load_dotenv
    load_dotenv()

    config_name = os.environ.get('FLASK_ENV', 'development')

    from app import create_app
    app = create_app(config_name)

    # Ensure instance folder exists for SQLite
    os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

    init_database(app)
    _print_banner(config_name)

    app.run(
        host      = '0.0.0.0',
        port      = int(os.environ.get('PORT', 5000)),
        debug     = app.config.get('DEBUG', False),
        use_reloader = app.config.get('DEBUG', False),
    )


if __name__ == '__main__':
    main()
