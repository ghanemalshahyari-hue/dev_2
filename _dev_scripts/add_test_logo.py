
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.department import Department

app = create_app()

with app.app_context():
    # Find a non-central department
    dept = Department.query.filter_by(is_central=False, is_active=True).first()
    if dept:
        dept.logo_file = 'logo.svg'
        db.session.commit()
        print(f"Added test logo to department: {dept.name}")
    else:
        print("No suitable department found.")
