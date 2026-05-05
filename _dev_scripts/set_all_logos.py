
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.department import Department

app = create_app()

with app.app_context():
    # Update all non-central departments to have the test logo
    departments = Department.query.filter_by(is_central=False, is_active=True).all()
    count = 0
    for dept in departments:
        # Assign logo if not already set (or overwrite to ensure uniformity for testing)
        dept.logo_file = 'logo.svg'
        count += 1
    
    db.session.commit()
    print(f"Updated {count} departments with 'logo.svg'.")
