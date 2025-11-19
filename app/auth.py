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
from .validators import is_valid_email, is_strong_password
from flask_dance.contrib.google import google
import os


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
        
        # Restrict signup to Colby College emails only
        if not email.endswith("@colby.edu"):
            flash("Please use your Colby College email address.", "danger")
            return redirect(url_for("auth.signup"))

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with that email already exists.", "warning")
            return redirect(url_for("auth.signup"))

        # Check password match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))
        
        # Validate strong password
        if not is_strong_password(password):
            flash("Password must be at least 12 characters and include both letters and numbers.", "danger")
            return redirect(url_for("auth.signup"))


        # Create new user with hashed password
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(name=name, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        # Generate verification token
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(email, salt="email-verify-salt")

        verify_url = url_for("auth.verify_email", token=token, _external=True)

        # Send verification email
        msg = Message(
            subject="Verify Your ColbyNow Account",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[email],
            body=(
                f"Hi {name},\n\n"
                f"Please verify your account by clicking the link below:\n{verify_url}\n\n"
                f"This link expires in 1 hour.\n\n"
                f"If you did not sign up, simply ignore this email."
            ),
        )

        current_app.extensions["mail"].send(msg)

        flash("Account created! Please check your email to verify your account.", "info")
        return redirect(url_for("auth.login"))


    return render_template("signup.html")


# ---------- LOGIN ----------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Empty fields
        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("auth.login"))

        # Retrieve user
        user = User.query.filter_by(email=email).first()

        # Timing protection
        if not user:
            check_password_hash(generate_password_hash("fallback123!"), password)
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        # Wrong password
        if not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        # STEP 4 — Prevent login if account is not verified
        if not user.is_verified:
            flash("Please verify your email before logging in. Check your inbox.", "warning")
            return redirect(url_for("auth.login"))

        # Success
        login_user(user, remember=bool(request.form.get("remember")))
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


# ---------- RESET PASSWORD ----------

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



# ---------- EMAIL VERIFICATION ----------
@auth.route("/verify/<token>")
def verify_email(token):
    """Verifies a user's email using the token sent after signup."""
    try:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        email = s.loads(token, salt="email-verify-salt", max_age=3600)
    except Exception:
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.signup"))

    # Find user
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.signup"))

    # If already verified
    if user.is_verified:
        flash("Your account is already verified. Please log in.", "info")
        return redirect(url_for("auth.login"))

    # Mark user as verified
    user.is_verified = True
    db.session.commit()

    flash("Your email has been verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))



# ---------- GOOGLE LOGIN ----------

@auth.route("/google")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("https://www.googleapis.com/oauth2/v3/userinfo")
    user_info = resp.json()

    email = user_info["email"]
    name = user_info.get("name", "Google User")

    # --- Restrict Google login to Colby emails ---
    if not email.endswith("@colby.edu"):
        flash("Please use your @colby.edu email address to sign in.", "danger")
        return redirect(url_for("auth.login"))

    # Check if user exists
    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(os.urandom(16).hex()),
            is_verified=True
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in with Google!", "success")
    return redirect(url_for("main.home"))