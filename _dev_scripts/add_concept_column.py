
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.department import Department
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking if 'concept_number' column exists in 'departments' table...")
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('departments')]
    
    if 'concept_number' not in columns:
        print("Adding 'concept_number' column...")
        with db.engine.connect() as conn:
            # SQLite specific ALTER TABLE
            conn.execute(text("ALTER TABLE departments ADD COLUMN concept_number INTEGER"))
            conn.commit()
        print("Column added successfully.")
    else:
        print("Column 'concept_number' already exists.")
