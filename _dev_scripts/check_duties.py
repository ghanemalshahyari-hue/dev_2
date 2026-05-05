

import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.department import Department
from app.models.duties import Duty


app = create_app()

with app.app_context():
    print("--- Departments ---")
    depts = Department.query.all()
    for d in depts:
        print(f"ID: {d.id}, Name: {d.name}, Code: {d.code}")

    print("\n--- Duties ---")
    duties = Duty.query.all()
    for duty in duties:
        print(f"ID: {duty.id}, DeptID: {duty.department_id}, Active: {duty.is_active}, Title: {duty.title}")

    print("\n--- Counts Check ---")
    for d in depts:
        count = Duty.query.filter_by(department_id=d.id, is_active=True).count()
        print(f"Dept: {d.name} (ID: {d.id}) -> Active Duties Count: {count}")
