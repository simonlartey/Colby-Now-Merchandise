from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)


from app.services.auth_service import (
    create_user,
    authenticate_user,
    verify_email_token,
    generate_password_reset,
    reset_password_with_token,
)
from flask_login import login_user, logout_user, login_required
from .models import User, db
from flask_dance.contrib.google import google
import os

# blueprint for authenticaiton routes
auth = Blueprint("auth", __name__)

# ---------- SIGNUP ----------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))

        user, error = create_user(first_name, last_name, email, password)

        if error:
            flash(error, "danger")
            return redirect(url_for("auth.signup"))

        flash("Account created! Please check your email to verify your account.", "info")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")



# ---------- LOGIN ----------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("auth.login"))

        user, error = authenticate_user(email, password)

        if error:
            flash(error, "danger")
            return redirect(url_for("auth.login"))

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
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        success = generate_password_reset(email)

        if not success:
            flash("No account found with that email address.", "danger")
            return redirect(url_for("auth.forgot_password"))

        flash("Password reset instructions have been sent to your email.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")



# ---------- RESET PASSWORD ----------
@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.reset_password", token=token))

        success = reset_password_with_token(token, new_password)

        if not success:
            flash("The reset link is invalid or has expired.", "danger")
            return redirect(url_for("auth.forgot_password"))

        flash("Your password has been reset successfully!", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)



# ---------- EMAIL VERIFICATION ----------
@auth.route("/verify/<token>")
def verify_email(token):
    success = verify_email_token(token)

    if not success:
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.signup"))

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
        # Split name into first/last
        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=generate_password_hash(os.urandom(16).hex()),
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in with Google!", "success")
    return redirect(url_for("main.home"))
