"""
Flask Extensions — Initialized here, bound to app in create_app().
Import these instances from anywhere in the app.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db           = SQLAlchemy()
login_manager = LoginManager()
csrf         = CSRFProtect()
