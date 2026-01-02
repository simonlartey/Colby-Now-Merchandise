# app/services/auth_service.py

from flask.helpers import url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app
from flask_mail import Message
from app.models import User, db
from app.utils.validators import is_strong_password
import os


def create_user(first_name, last_name, email, password, confirm_password):
    if not email.endswith("@colby.edu"):
        return None, "Please use your Colby College email address."

    if User.query.filter_by(email=email).first():
        return None, "An account with that email already exists."

    if password != confirm_password:
        return None, "Passwords do not match."

    if not is_strong_password(password):
        return (
            None,
            "Password must be at least 12 characters and include letters and numbers.",
        )

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_password,
        is_verified=False,
    )

    db.session.add(user)
    db.session.commit()

    send_verification_email(user)

    return user, None


def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()

    if not user:
        check_password_hash(generate_password_hash("fallback123!"), password)
        return None, "Invalid email or password."

    if not check_password_hash(user.password, password):
        return None, "Invalid email or password."

    if not user.is_verified:
        return None, "Please verify your email before logging in."

    return user, None


def send_verification_email(user):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = s.dumps(user.email, salt="email-verify-salt")

    verify_url = url_for("auth.verify_email", token=token, _external=True)

    msg = Message(
        subject="Verify Your ColbyNow Account",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[user.email],
        body=(
            f"Hi {user.first_name},\n\n"
            f"Please verify your account:\n{verify_url}\n\n"
            f"This link expires in 1 hour."
        ),
    )

    current_app.extensions["mail"].send(msg)


def resend_verification_email(email: str) -> bool:
    """
    Resends a verification email if a user exists and is not verified.

    Params
    ------
    email: str
        The email address that the verification email is to be sent to.

    Returns
    -------
    success: bool
        `True` if the verification email was sent to the given email address. Otherwise `False`.
    """
    user = User.query.filter_by(email=email).first()

    if not user:
        current_app.logger.warning(
            f"Error sending verification email: user with email `{email}` does not exist."
        )
        return False

    if user.is_verified:
        current_app.logger.warning(
            f"Error sending verification email: user already verified"
        )
        return False

    send_verification_email(user)
    return True


def verify_email_token(token: str) -> bool:
    """
    Verifies a user's email address given an email verification token.

    Parameters
    ----------
    token : str
        The email verification token.

    Returns
    -------
    bool
        `True` if the token is valid and the user exists, `False` otherwise.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(token, salt="email-verify-salt", max_age=3600)
    except (BadSignature, SignatureExpired):
        current_app.logger.exception("There was an error resetting the password")
        return False

    user = User.query.filter_by(email=email).first()
    if not user:
        return False

    if user.is_verified:
        return True

    user.is_verified = True
    db.session.commit()
    return True


def generate_password_reset(email):
    user = User.query.filter_by(email=email).first()
    if not user:
        return None

    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = s.dumps(email, salt="password-reset-salt")

    reset_url = url_for("auth.reset_password", token=token, _external=True)

    msg = Message(
        subject="Password Reset Request",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[email],
        body=f"Reset your password:\n{reset_url}",
    )

    current_app.extensions["mail"].send(msg)
    return True


def reset_password_with_token(token: str, new_password: str) -> tuple[bool, str]:
    """
    Resets the user's password using a provided token.

    Parameters
    ----------
    token : str
        The password reset token.
    new_password : str
        The new password to be set.

    Returns
    -------
    success : bool
        `True` if the password was successfully reset, `False` otherwise.
    message : str
        A message indicating the result of the operation.
    """
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    try:
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except (BadSignature, SignatureExpired) as e:
        current_app.logger.exception("There was an error resetting the password")
        return False, "Invalid or expired password reset token"

    user = User.query.filter_by(email=email).first()
    if not user:
        return False, "Invalid or expired password reset token"

    if not is_strong_password(new_password):
        return (
            False,
            "Password must be at least 12 characters and include letters and numbers.",
        )

    user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
    db.session.commit()
    return True, "Password reset successful"
