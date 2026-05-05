"""
Enterprise Dashboard Application Factory — v2.0

Creates and configures the Flask application.
All extensions and blueprints are initialized here.
"""

from __future__ import annotations

from flask import Flask, render_template

from app.extensions import db, login_manager, csrf
from app.config import config


def create_app(config_name: str = 'default') -> Flask:
    """
    Application factory.

    Args:
        config_name: 'development' | 'production' | 'testing'

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_context_processors(app)

    return app


# ─── Private helpers ──────────────────────────────────────────────────────────

def _register_extensions(app: Flask) -> None:
    """Initialize all Flask extensions."""
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Login manager configuration
    login_manager.login_view          = 'auth.login'
    login_manager.login_message       = 'Please sign in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection  = 'strong'

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User
        return User.get_by_id(user_id)


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    from app.auth      import auth_bp
    from app.dashboard import dashboard_bp
    from app.admin     import admin_bp
    from app.access    import access_bp
    from app.api       import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(access_bp)
    app.register_blueprint(api_bp)

    # Root → dashboard index
    from flask import redirect, url_for

    @app.route('/')
    def root():
        return redirect(url_for('dashboard.index'))


def _register_error_handlers(app: Flask) -> None:
    """Register custom HTTP error pages."""

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('errors/401.html'), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500


def _register_context_processors(app: Flask) -> None:
    """Inject global variables into every template."""
    from datetime import datetime
    from app.models.role import PERMISSIONS

    @app.context_processor
    def inject_globals():
        return {
            'PERMISSIONS': PERMISSIONS,
            'now':         datetime.utcnow,
            'app_name':    app.config.get('APP_NAME', 'Enterprise Dashboard'),
        }
