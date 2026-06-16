"""
Adds a 'responsible_name' column to the 'departments' table.

This separates the person's NAME from their TITLE/ROLE (responsible_person):
- responsible_person → the role/title (e.g., "رئيس هيئة العمليات والخطط...")
- responsible_name   → the actual person's name (e.g., "محمد أحمد")

Run once: python _dev_scripts/add_responsible_name_column.py
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking if 'responsible_name' column exists in 'departments' table...")
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('departments')]

    if 'responsible_name' not in columns:
        print("Adding 'responsible_name' column...")
        with db.engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE departments ADD COLUMN responsible_name VARCHAR(120) DEFAULT ''"
            ))
            conn.commit()
        print("Column added successfully.")
    else:
        print("Column 'responsible_name' already exists.")
