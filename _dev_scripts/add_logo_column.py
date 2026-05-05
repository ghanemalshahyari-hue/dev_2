
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.department import Department
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking if 'logo_file' column exists in 'departments' table...")
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('departments')]
    
    if 'logo_file' not in columns:
        print("Adding 'logo_file' column...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE departments ADD COLUMN logo_file VARCHAR(120)"))
            conn.commit()
        print("Column added successfully.")
    else:
        print("Column 'logo_file' already exists.")
