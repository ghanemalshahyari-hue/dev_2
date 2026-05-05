"""Auth Blueprint — Login form."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """LDAP login form with CSRF protection."""

    username = StringField(
        'Username',
        validators=[
            DataRequired(message='Username is required.'),
            Length(min=2, max=80, message='Username must be 2–80 characters.'),
        ],
        render_kw={'autocomplete': 'username', 'autofocus': True},
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=2, max=128),
        ],
        render_kw={'autocomplete': 'current-password'},
    )

    remember_me = BooleanField('Keep me signed in (shared device warning)')
    submit      = SubmitField('Sign In')
