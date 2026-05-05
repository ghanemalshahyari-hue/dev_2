"""
Application Configuration Classes
Enterprise Dashboard System — v2.0

All sensitive values loaded from environment variables.
See .env.example for full list of required variables.
"""

import os
from datetime import timedelta
from typing import Dict, Type

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration — shared across all environments."""

    # ─── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'CHANGE-ME-IN-PRODUCTION-USE-32-BYTE-RANDOM'

    # ─── Database ─────────────────────────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # ─── Session ──────────────────────────────────────────────────────────────
    SESSION_COOKIE_SECURE     = True
    SESSION_COOKIE_HTTPONLY   = True
    SESSION_COOKIE_SAMESITE   = 'Strict'
    SESSION_COOKIE_NAME       = 'enterprise_session'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # ─── CSRF ─────────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED    = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # ─── LDAP ─────────────────────────────────────────────────────────────────
    LDAP_SERVER            = os.environ.get('LDAP_SERVER', 'ldaps://ldap.company.local:636')
    LDAP_BASE_DN           = os.environ.get('LDAP_BASE_DN', 'dc=company,dc=local')
    LDAP_BIND_DN           = os.environ.get('LDAP_BIND_DN', '')
    LDAP_BIND_PASSWORD     = os.environ.get('LDAP_BIND_PASSWORD', '')
    LDAP_USER_SEARCH_BASE  = os.environ.get('LDAP_USER_SEARCH_BASE', 'ou=users')
    LDAP_USER_SEARCH_FILTER = os.environ.get('LDAP_USER_SEARCH_FILTER', '(sAMAccountName={username})')
    LDAP_USE_SSL           = os.environ.get('LDAP_USE_SSL', 'True').lower() == 'true'
    LDAP_SIMULATION_MODE   = os.environ.get('LDAP_SIMULATION_MODE', 'False').lower() == 'true'

    # ─── Auth Security ────────────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS       = 5
    LOCKOUT_DURATION_MINUTES = 15
    PASSWORD_MIN_LENGTH      = 8   # for local/dev accounts

    # ─── Application ──────────────────────────────────────────────────────────
    ITEMS_PER_PAGE           = 25
    APP_NAME                 = os.environ.get('APP_NAME', 'Enterprise Dashboard')

    # ─── Default Departments ──────────────────────────────────────────────────
    DEFAULT_DEPARTMENTS = [
        # index 0 → is_central=True → الاستراتيجية (CEO hub)
        {'code': 'STRATEGY', 'name': 'الاستراتيجية',    'color': '#4F8EF7', 'icon': 'bi-bullseye',            'order_index': 0},
        {'code': 'GRP1',     'name': 'المجموعة الأولى',  'color': '#34D399', 'icon': 'bi-1-circle-fill',       'order_index': 1},
        {'code': 'GRP2',     'name': 'المجموعة الثانية', 'color': '#F59E0B', 'icon': 'bi-2-circle-fill',       'order_index': 2},
        {'code': 'GRP3',     'name': 'المجموعة الثالثة', 'color': '#EF4444', 'icon': 'bi-3-circle-fill',       'order_index': 3},
        {'code': 'GRP4',     'name': 'المجموعة الرابعة', 'color': '#A78BFA', 'icon': 'bi-4-circle-fill',       'order_index': 4},
        {'code': 'GRP5',     'name': 'المجموعة الخامسة', 'color': '#EC4899', 'icon': 'bi-5-circle-fill',       'order_index': 5},
        {'code': 'GRP6',     'name': 'المجموعة السادسة', 'color': '#14B8A6', 'icon': 'bi-6-circle-fill',       'order_index': 6},
    ]

    @staticmethod
    def init_app(app) -> None:  # type: ignore[override]
        pass


class DevelopmentConfig(Config):
    """Development — LDAP simulation, SQLite, debug ON."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "instance", "dev.db")}'

    # Relax for dev
    SESSION_COOKIE_SECURE  = False
    LDAP_SIMULATION_MODE   = True


class TestingConfig(Config):
    """Testing — in-memory SQLite, CSRF off."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED        = False
    SESSION_COOKIE_SECURE   = False
    LDAP_SIMULATION_MODE    = True


class ProductionConfig(Config):
    """Production — strict security, no debug."""

    DEBUG   = False
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    LDAP_USE_SSL            = True
    LDAP_SIMULATION_MODE    = False

    @staticmethod
    def init_app(app) -> None:  # type: ignore[override]
        Config.init_app(app)
        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists('logs'):
            os.makedirs('logs')

        file_handler = RotatingFileHandler(
            'logs/enterprise.log', maxBytes=10_485_760, backupCount=10
        )
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


config: Dict[str, Type[Config]] = {
    'development': DevelopmentConfig,
    'testing':     TestingConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
