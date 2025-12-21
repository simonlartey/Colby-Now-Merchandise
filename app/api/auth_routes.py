"""
Auth API endpoints
REST authentication routes
"""

from flask import request
from flask_login import login_user, logout_user, current_user

from app.services.auth_service import (
    create_user,
    authenticate_user,
    generate_password_reset,
    reset_password_with_token,
    verify_email_token,
)

from .responses import (
    success_response,
    error_response,
    require_api_auth,
)


def register_routes(api):
    """Register auth routes to the API blueprint."""

    @api.route("/auth/signup", methods=["POST"])
    def api_signup():
        data = request.get_json() or {}

        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        if password != confirm_password:
            return error_response("Passwords do not match", 400)

        user, error = create_user(first_name, last_name, email, password)

        if error:
            return error_response(error, 400)

        return success_response(
            message="Account created. Please verify your email."
        )

    @api.route("/auth/login", methods=["POST"])
    def api_login():
        data = request.get_json() or {}

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user, error = authenticate_user(email, password)

        if error:
            return error_response(error, 401)

        login_user(user)

        return success_response(
            message="Login successful"
        )

    @api.route("/auth/logout", methods=["POST"])
    @require_api_auth
    def api_logout():
        logout_user()
        return success_response(message="Logged out successfully")

    @api.route("/auth/forgot-password", methods=["POST"])
    def api_forgot_password():
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()

        success = generate_password_reset(email)

        if not success:
            return error_response("No account found with that email", 404)

        return success_response(
            message="Password reset instructions sent"
        )

    @api.route("/auth/reset-password", methods=["POST"])
    def api_reset_password():
        data = request.get_json() or {}

        token = data.get("token")
        new_password = data.get("password")

        if not token or not new_password:
            return error_response("Token and password required", 400)

        success = reset_password_with_token(token, new_password)

        if not success:
            return error_response("Invalid or expired token", 400)

        return success_response(message="Password reset successful")

    @api.route("/auth/verify/<token>", methods=["GET"])
    def api_verify_email(token):
        success = verify_email_token(token)

        if not success:
            return error_response("Invalid or expired verification token", 400)

        return success_response(message="Email verified successfully")

    @api.route("/auth/me", methods=["GET"])
    @require_api_auth
    def api_me():
        return success_response(
            data={
                "id": current_user.id,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "is_verified": current_user.is_verified,
            }
        )
