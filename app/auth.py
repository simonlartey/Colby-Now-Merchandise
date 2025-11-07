from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from itsdangerous import URLSafeTimedSerializer
from .models import User, db

# blueprint for authenticaiton routes
auth = Blueprint("auth", __name__)


# ---------- SIGNUP ----------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Safely retrieve and clean form data
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with that email already exists.", "warning")
            return redirect(url_for("auth.signup"))

        # Check password match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))

        # Create new user with hashed password
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(name=name, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")


# ---------- LOGIN ----------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        remember = True if request.form.get("remember") else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)
        flash("Login successful!", "success")
        return redirect(url_for("main.home"))

    return render_template("login.html")


# ---------- LOGOUT ----------
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ---------- FORGOT PASSWORD ----------
@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Handles user password reset requests."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with that email address.", "danger")
            return redirect(url_for("auth.forgot_password"))

        # Generate password reset token
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(email, salt="password-reset-salt")

        # Create password reset URL
        reset_url = url_for("auth.reset_password", token=token, _external=True)

        # Create a password reset email
        msg = Message(
            subject="Password Reset Request - Colby Now Merchandise",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[email],
            body=f"Hi {user.name},\n\nTo reset your password, please click the following link:\n{reset_url}\n\nThis link will expire in 1 hour.\n\nIf you did not request this, please ignore this email.",
        )

        # Send email using current_app’s mail instance
        current_app.extensions["mail"].send(msg)

        flash("Password reset instructions have been sent to your email.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Resets the user's password using a token sent via email."""
    try:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except Exception:
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.reset_password", token=token))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("auth.signup"))

        user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
        db.session.commit()

        flash("Your password has been reset successfully!", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
