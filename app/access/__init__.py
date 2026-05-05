"""Access Blueprint package."""

from flask import Blueprint

access_bp = Blueprint('access', __name__, url_prefix='/access')

from app.access import routes  # noqa: E402, F401
