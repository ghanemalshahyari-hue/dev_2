"""
Permission Decorators — Route-level access control.

Usage:
    @require_permission(PERMISSIONS['DEPUTY'])
    def my_view():
        ...
"""

from __future__ import annotations
from functools import wraps
from typing import Callable

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def require_permission(min_level: int) -> Callable:
    """
    Decorator: allows access only if current_user.permission_level >= min_level.
    Returns 403 for AJAX requests, redirects with flash for browser requests.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not current_user.has_permission(min_level):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_role(role_code: str) -> Callable:
    """Decorator: allows access only if current_user has exactly this role (or DEVELOPER)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role_code not in (role_code, 'DEVELOPER'):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
