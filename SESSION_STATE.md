# Session State - Enterprise Dashboard Project
**Last Updated:** February 18, 2026

## Project Overview
Building an enterprise website with LDAP authentication for a private offline server.

### Key Requirements
- 5-level user hierarchy (Super Admin → Admin → Group Admin → Team Lead → User)
- CEO dashboard with circular visualization of 7 departments
- Each department shows: competence % and completion %
- Multi-level access request workflow with rejection reasons
- Fully offline deployment (all libraries bundled locally)

## Tech Stack
- **Backend:** Flask 3.0.0, SQLAlchemy 2.x, Flask-Login, Flask-WTF
- **Auth:** ldap3 library with simulation mode for development
- **Frontend:** Bootstrap 5.3.2 (bundled), Bootstrap Icons 1.11.2, Vanilla JS
- **Password Hashing:** Argon2

## Completed Tasks ✅
1. PROJECT_RULES.md - Complete development standards
2. Project folder structure created
3. All database models (User, Role, Department, AccessRequest, AuditLog, DepartmentMetrics)
4. LDAP authentication module with simulation mode
5. Access request workflow with approval chain
6. Login page (enterprise gradient design)
7. CEO dashboard with 7 circular department visualization
8. All templates (auth, dashboard, admin, access, errors)
9. Static assets (Bootstrap CSS/JS, Icons with fonts, custom.css, app.js)
10. Context processor fix for `now()` function

## Test Credentials (LDAP Simulation Mode)
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Super Admin |
| manager | manager123 | Admin |
| groupadmin | groupadmin123 | Group Admin |
| lead | lead123 | Team Lead |
| user | user123 | User |

## Project Structure
```
dev_2/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py, role.py, department.py
│   │   ├── access_request.py, audit.py, metrics.py
│   ├── auth/                # Authentication blueprint
│   │   ├── ldap_client.py, forms.py, routes.py
│   ├── dashboard/           # Dashboard blueprint
│   ├── admin/               # Admin blueprint
│   ├── access/              # Access requests blueprint
│   ├── api/                 # API blueprint
│   ├── utils/               # Decorators, helpers
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, fonts (offline)
├── run.py                   # Development runner
├── wsgi.py                  # Production WSGI
├── requirements.txt         # Dependencies
├── PROJECT_RULES.md         # Development standards
└── instance/                # SQLite database
```

## How to Run
```bash
cd c:\Users\EngCoder\Desktop\Ghanem\dev_2
.venv\Scripts\python run.py
```
Open http://127.0.0.1:5000

## Remaining Tasks
- [ ] Download Chart.js for potential dashboard charts
- [ ] Additional admin templates (user_detail, user_edit, audit_log, settings)
- [ ] Production configuration and deployment guide
- [ ] Unit tests

## Recent Fix
Fixed `jinja2.exceptions.UndefinedError: 'now' is undefined` by adding `now: datetime.now` to context processor in `app/__init__.py`

## Database Location
SQLite database: `instance/enterprise.db` (auto-created on first run)

## Notes for Continuation
- The server was running successfully before this save
- All core functionality is implemented
- LDAP simulation mode is enabled for offline testing
- The 7 default departments are created automatically on first run
