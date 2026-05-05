# PROJECT RULES & STANDARDS
## Enterprise Dashboard System with LDAP Authentication

> **IMPORTANT**: This document is the SOURCE OF TRUTH for all development.
> All agents and developers MUST follow these rules consistently.
> DO NOT modify any code without consulting this document first.

---

## 1. PROJECT OVERVIEW

### 1.1 Purpose
Enterprise-grade dashboard system for CEO-level visibility of departmental data completeness and competence metrics.

### 1.2 Key Requirements
- **Deployment**: Private offline server (air-gapped)
- **Authentication**: LDAP server integration
- **Security Level**: Maximum (enterprise/military grade)
- **Lifespan Target**: 10+ years
- **Scale**: Large company with hierarchical structure

---

## 2. TECHNOLOGY STACK (MANDATORY)

### 2.1 Backend
```
Framework:      Flask 3.x
Database:       SQLite (dev) / PostgreSQL (prod)
ORM:            SQLAlchemy 2.x
LDAP:           python-ldap / ldap3
Session:        Flask-Session (server-side)
Security:       Flask-Talisman, Flask-WTF (CSRF)
Password Hash:  argon2-cffi (backup auth)
```

### 2.2 Frontend (ALL OFFLINE - NO CDN)
```
CSS Framework:  Bootstrap 5.3.x (bundled)
Icons:          Bootstrap Icons 1.11.x (bundled)
Charts:         Chart.js 4.x (bundled)
JavaScript:     Vanilla JS (no jQuery dependency)
Fonts:          System fonts (no external fonts)
```

### 2.3 Required Python Packages
```
flask==3.0.0
flask-sqlalchemy==3.1.1
flask-login==0.6.3
flask-wtf==1.2.1
flask-session==0.5.0
flask-talisman==0.8.1
ldap3==2.9.1
argon2-cffi==23.1.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

---

## 3. SECURITY RULES (CRITICAL)

### 3.1 Authentication
- [ ] All passwords MUST be hashed using Argon2
- [ ] LDAP binds MUST use LDAPS (port 636) or STARTTLS
- [ ] Session tokens MUST be server-side (not JWT in cookies)
- [ ] Session timeout: 30 minutes inactive
- [ ] Maximum login attempts: 5 before lockout
- [ ] Account lockout duration: 15 minutes

### 3.2 Authorization
- [ ] ALL routes MUST check user permissions
- [ ] Role-based access control (RBAC) is MANDATORY
- [ ] Audit log ALL access attempts and changes
- [ ] Implement principle of least privilege

### 3.3 Data Protection
- [ ] CSRF protection on ALL forms
- [ ] Content Security Policy headers
- [ ] XSS prevention (escape all user input)
- [ ] SQL injection prevention (use ORM only)
- [ ] HTTPS only (no HTTP fallback)
- [ ] Secure cookie flags (HttpOnly, Secure, SameSite=Strict)

### 3.4 Headers (Flask-Talisman Config)
```python
TALISMAN_CONFIG = {
    'force_https': True,
    'strict_transport_security': True,
    'session_cookie_secure': True,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
    }
}
```

---

## 4. الهيكل التنظيمي (USER HIERARCHY)

### 4.1 الأدوار (Role Definitions)

| المستوى | الدور | الصلاحيات | النطاق |
|---------|-------|-----------|--------|
| 1 | **المدير (Director)** | نظرة عامة، مؤشرات الأداء، التنبيهات، تقدم الخطة | عام |
| 2 | **السكرتير (Secretary)** | ترتيب وتخطيط ومتابعة المجموعات، الإطار الزمني، ورش العمل، النماذج | عام |
| 3 | **نائب المدير (Deputy)** | اتخاذ القرارات والاعتمادات بناءً على ما يرتبه السكرتير | عام |
| 4 | **مدير المجموعة (Group Admin)** | إدارة مجموعة واحدة، إدخال البيانات، التقارير | مجموعة واحدة |
| 5 | **مستخدم (User)** | عرض البيانات المخصصة، طلب الصلاحيات | شخصي |

### 4.2 أكواد الصلاحيات
```python
PERMISSIONS = {
    'DIRECTOR': 100,      # المدير
    'SECRETARY': 90,      # السكرتير
    'DEPUTY': 80,         # نائب المدير
    'GROUP_ADMIN': 60,    # مدير المجموعة
    'USER': 20,           # مستخدم
}
```

### 4.3 هيكل العمل
```
                     المدير (Director)
                          │
                    نظرة عامة فقط
                    - المجموعات السبع
                    - مؤشرات الأداء
                    - التنبيهات المهمة
                    - تقدم الخطة
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
   السكرتير (Secretary)              نائب المدير (Deputy)
        │                                   │
   يرتب ويخطط ويتابع:                    يقرر ويعتمد:
   - الإطار الزمني                    - بناءً على ترتيبات
     (شهري/سنوي)                       السكرتير
   - ورش العمل                        - الموافقات
   - النماذج                          - التوجيهات
   - متابعة المجموعات
   - الشاشة الدائرية
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                   7 مجموعات (موحدة)
                   - نسبة الكفاءة %
                   - نسبة الإنجاز %
                   - التعريف/الوصف
                   - المسؤول
                   (قابلة للإخفاء/الإضافة/الحذف)
```

---

## 5. DATABASE SCHEMA

### 5.1 Core Tables

```sql
-- Users (LDAP-linked)
users
├── id (UUID, PK)
├── ldap_dn (VARCHAR, UNIQUE, NOT NULL)
├── username (VARCHAR, UNIQUE, NOT NULL)
├── email (VARCHAR, NOT NULL)
├── full_name (VARCHAR, NOT NULL)
├── role_id (FK → roles.id)
├── department_id (FK → departments.id)
├── team_id (FK → teams.id, NULLABLE)
├── is_active (BOOLEAN, DEFAULT TRUE)
├── created_at (TIMESTAMP)
├── updated_at (TIMESTAMP)
└── last_login (TIMESTAMP)

-- Roles
roles
├── id (INT, PK)
├── name (VARCHAR, UNIQUE)
├── permission_level (INT)
└── description (TEXT)

-- Departments (The 7 Groups)
departments
├── id (INT, PK)
├── name (VARCHAR, UNIQUE)
├── code (VARCHAR(10), UNIQUE)
├── color (VARCHAR(7)) -- Hex color for dashboard
├── icon (VARCHAR(50)) -- Bootstrap icon name
├── order_index (INT) -- Position in circular dashboard
└── is_active (BOOLEAN)

-- Teams (Sub-divisions within departments)
teams
├── id (INT, PK)
├── name (VARCHAR)
├── department_id (FK → departments.id)
└── lead_id (FK → users.id)

-- Access Requests
access_requests
├── id (UUID, PK)
├── requester_id (FK → users.id)
├── requested_permission (VARCHAR)
├── requested_scope (VARCHAR)
├── status (ENUM: pending, approved, rejected)
├── current_approver_level (INT)
├── created_at (TIMESTAMP)
└── resolved_at (TIMESTAMP)

-- Access Request Approvals
access_approvals
├── id (UUID, PK)
├── request_id (FK → access_requests.id)
├── approver_id (FK → users.id)
├── approver_role_level (INT)
├── decision (ENUM: approved, rejected)
├── rejection_reason (TEXT, NULLABLE)
├── decided_at (TIMESTAMP)

-- Audit Log
audit_log
├── id (UUID, PK)
├── user_id (FK → users.id)
├── action (VARCHAR)
├── resource_type (VARCHAR)
├── resource_id (VARCHAR)
├── old_value (JSON)
├── new_value (JSON)
├── ip_address (VARCHAR)
├── timestamp (TIMESTAMP)

-- Department Metrics (For Dashboard)
department_metrics
├── id (UUID, PK)
├── department_id (FK → departments.id)
├── metric_date (DATE)
├── competence_percentage (DECIMAL) -- Data quality/provision
├── completion_percentage (DECIMAL) -- Work completed
├── data_entries_required (INT)
├── data_entries_completed (INT)
├── quality_score (DECIMAL)
├── updated_by (FK → users.id)
└── updated_at (TIMESTAMP)
```

---

## 6. THE 7 DEPARTMENTS (CEO Dashboard Groups)

### 6.1 Default Configuration
```python
DEPARTMENTS = [
    {'code': 'HR', 'name': 'Human Resources', 'color': '#FF6384', 'icon': 'bi-people-fill'},
    {'code': 'FIN', 'name': 'Finance', 'color': '#36A2EB', 'icon': 'bi-currency-dollar'},
    {'code': 'IT', 'name': 'Information Technology', 'color': '#FFCE56', 'icon': 'bi-pc-display'},
    {'code': 'OPS', 'name': 'Operations', 'color': '#4BC0C0', 'icon': 'bi-gear-fill'},
    {'code': 'MKT', 'name': 'Marketing', 'color': '#9966FF', 'icon': 'bi-megaphone-fill'},
    {'code': 'R&D', 'name': 'Research & Development', 'color': '#FF9F40', 'icon': 'bi-lightbulb-fill'},
    {'code': 'QA', 'name': 'Quality Assurance', 'color': '#C9CBCF', 'icon': 'bi-patch-check-fill'},
]
```

### 6.2 Dashboard Metrics (Per Department)
1. **Competence %**: Quality of data provided (0-100%)
2. **Completion %**: Data entry completion status (0-100%)

---

## 7. FOLDER STRUCTURE (MANDATORY)

```
project_root/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Flask extensions init
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User model
│   │   ├── role.py              # Role model
│   │   ├── department.py        # Department model
│   │   ├── access_request.py    # Access request models
│   │   └── audit.py             # Audit log model
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py            # Login/logout routes
│   │   ├── forms.py             # Login forms
│   │   └── ldap_client.py       # LDAP connection handler
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes.py            # Admin panel routes
│   │   └── forms.py             # Admin forms
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── routes.py            # Dashboard routes
│   │   └── services.py          # Dashboard data services
│   ├── access/
│   │   ├── __init__.py
│   │   ├── routes.py            # Access request routes
│   │   └── services.py          # Access workflow services
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # Internal API endpoints
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py        # Permission decorators
│   │   ├── helpers.py           # Utility functions
│   │   └── audit.py             # Audit logging helpers
│   ├── static/
│   │   ├── css/
│   │   │   ├── bootstrap.min.css
│   │   │   ├── bootstrap-icons.css
│   │   │   └── custom.css       # Custom styles
│   │   ├── js/
│   │   │   ├── bootstrap.bundle.min.js
│   │   │   ├── chart.min.js
│   │   │   └── app.js           # Custom JavaScript
│   │   ├── fonts/
│   │   │   └── bootstrap-icons.woff2
│   │   └── img/
│   │       └── logo.svg
│   └── templates/
│       ├── base.html            # Base template
│       ├── auth/
│       │   └── login.html       # Login page
│       ├── dashboard/
│       │   ├── ceo.html         # CEO circular dashboard
│       │   ├── admin.html       # Admin dashboard
│       │   └── user.html        # User dashboard
│       ├── admin/
│       │   ├── users.html       # User management
│       │   └── settings.html    # System settings
│       ├── access/
│       │   ├── request.html     # New access request
│       │   └── pending.html     # Pending approvals
│       └── components/
│           ├── navbar.html      # Navigation component
│           ├── sidebar.html     # Sidebar component
│           └── alerts.html      # Alert messages
├── migrations/                   # Database migrations
├── tests/                        # Unit tests
├── instance/
│   └── config.py                # Instance-specific config
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── wsgi.py                       # WSGI entry point
├── PROJECT_RULES.md              # THIS FILE
└── README.md                     # Project documentation
```

---

## 8. UI/UX STANDARDS

### 8.1 Design Principles
- **Clean & Professional**: No animations unless functional
- **Consistent**: Same patterns across all pages
- **Accessible**: WCAG 2.1 AA compliant
- **Responsive**: Works on all screen sizes
- **Fast**: Minimal JavaScript, server-side rendering

### 8.2 Color Scheme
```css
:root {
    --primary: #0d6efd;      /* Primary actions */
    --secondary: #6c757d;    /* Secondary elements */
    --success: #198754;      /* Success/approved */
    --danger: #dc3545;       /* Error/rejected */
    --warning: #ffc107;      /* Pending/attention */
    --info: #0dcaf0;         /* Information */
    --dark: #212529;         /* Text/headers */
    --light: #f8f9fa;        /* Backgrounds */
    --bg-gradient: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
```

### 8.3 Typography
- **Headings**: System font stack (native performance)
- **Body**: 16px base size
- **Font Stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`

### 8.4 Login Page Requirements
- Full-page background with gradient
- Centered login card with shadow
- Company logo placeholder
- Remember me option (with security warning)
- Clear error messages
- LDAP connection status indicator
- No external resources

### 8.5 CEO Dashboard Requirements
- **Circular Layout**: 7 segments arranged in a circle
- **Each Segment Shows**:
  - Department name
  - Competence % (color-coded ring)
  - Completion % (inner ring)
  - Click to drill down
- **Center**: Overall company metrics
- **Real-time**: Updates without page refresh (polling)

---

## 9. CODING STANDARDS

### 9.1 Python
```python
# Use type hints ALWAYS
def get_user(user_id: str) -> Optional[User]:
    pass

# Use docstrings for all functions
def calculate_metrics(department_id: int) -> Dict[str, float]:
    """
    Calculate competence and completion metrics for a department.
    
    Args:
        department_id: The department's database ID
        
    Returns:
        Dictionary with 'competence' and 'completion' percentages
    """
    pass

# Constants in UPPER_SNAKE_CASE
MAX_LOGIN_ATTEMPTS = 5

# Classes in PascalCase
class AccessRequest:
    pass

# Functions/variables in snake_case
def process_access_request():
    pass
```

### 9.2 HTML/Jinja2
```html
<!-- Use semantic HTML -->
<header>, <main>, <nav>, <section>, <article>, <footer>

<!-- Always escape variables -->
{{ user.name }}  <!-- Auto-escaped -->
{{ user.bio|safe }}  <!-- Only when safe! -->

<!-- Use template inheritance -->
{% extends "base.html" %}
{% block content %}{% endblock %}
```

### 9.3 JavaScript
```javascript
// Use const/let, never var
const API_URL = '/api';
let currentUser = null;

// Use async/await
async function fetchMetrics() {
    const response = await fetch('/api/metrics');
    return response.json();
}

// Use strict mode
'use strict';
```

### 9.4 CSS
```css
/* Use BEM naming convention */
.dashboard__card {}
.dashboard__card--active {}
.dashboard__card-title {}

/* Avoid !important */
/* Use CSS custom properties */
.button {
    background: var(--primary);
}
```

---

## 10. API ENDPOINTS

### 10.1 Authentication
```
POST /auth/login          # LDAP login
POST /auth/logout         # Logout
GET  /auth/session        # Check session status
```

### 10.2 Dashboard
```
GET  /api/dashboard/overview          # CEO overview
GET  /api/dashboard/department/<id>   # Department detail
GET  /api/dashboard/metrics           # All metrics
POST /api/dashboard/metrics           # Update metrics
```

### 10.3 Access Management
```
GET  /api/access/requests             # List my requests
POST /api/access/requests             # Create request
GET  /api/access/pending              # Pending approvals (for approvers)
POST /api/access/approve/<id>         # Approve request
POST /api/access/reject/<id>          # Reject request (requires reason)
```

### 10.4 Admin
```
GET  /api/admin/users                 # List users
POST /api/admin/users                 # Create user
PUT  /api/admin/users/<id>            # Update user
GET  /api/admin/audit-log             # View audit log
```

---

## 11. TESTING REQUIREMENTS

### 11.1 Minimum Coverage
- Unit tests: 80%+ coverage
- Integration tests for all API endpoints
- Security tests for authentication

### 11.2 Test Files
```
tests/
├── conftest.py           # Pytest fixtures
├── test_auth.py          # Authentication tests
├── test_dashboard.py     # Dashboard tests
├── test_access.py        # Access request tests
└── test_security.py      # Security tests
```

---

## 12. DEPLOYMENT CHECKLIST

### 12.1 Pre-Deployment
- [ ] All dependencies bundled (no internet required)
- [ ] Static files minified
- [ ] Debug mode OFF
- [ ] Secret keys generated (32+ bytes)
- [ ] HTTPS certificates installed
- [ ] Database migrations applied
- [ ] Initial admin user created

### 12.2 Environment Variables
```bash
# .env (NEVER commit this file)
SECRET_KEY=<generate-32-byte-key>
DATABASE_URL=postgresql://user:pass@localhost/dbname
LDAP_SERVER=ldaps://ldap.company.local:636
LDAP_BASE_DN=dc=company,dc=local
LDAP_BIND_DN=cn=service,dc=company,dc=local
LDAP_BIND_PASSWORD=<secure-password>
SESSION_LIFETIME_MINUTES=30
```

---

## 13. VERSION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-17 | System | Initial project rules |

---

## 14. AGENT INSTRUCTIONS

> **FOR AI AGENTS**: When modifying this codebase:
> 1. ALWAYS read this file first
> 2. Follow the folder structure EXACTLY
> 3. Use the specified technology stack ONLY
> 4. Implement security rules WITHOUT exception
> 5. Test all changes before committing
> 6. Update version history when making significant changes
> 7. NEVER remove or weaken security measures
> 8. Ask for clarification rather than guessing

---

*This document was generated for the Enterprise Dashboard Project.*
*Last Updated: 2026-02-17*
