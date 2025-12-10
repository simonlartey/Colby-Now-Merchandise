from flask import Flask, app, redirect, url_for, flash
from flask_login import LoginManager
from flask_mail import Mail
from flask_dance.contrib.google import make_google_blueprint
from .models import db, User
from .auth import auth
from .main import main
import os
from werkzeug.exceptions import RequestEntityTooLarge
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()


# Create a Mail instance globally
mail = Mail()

# Initialize Flask-Migrate
migrate = Migrate()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    os.makedirs(app.instance_path, exist_ok=True)

    # Basic app configuration
    app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

    # Get database URL
    database_url = os.getenv("DATABASE_URL", "sqlite:///users.db")

    if database_url == "sqlite:///users.db":
        database_url = f"sqlite:///{os.path.join(app.instance_path, 'users.db')}"

    # Format Postgres URLs for SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max uploaded file size

    # Mail configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

    # Stripe Configuration
    app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY")
    app.config["STRIPE_PUBLIC_KEY"] = os.getenv("STRIPE_PUBLIC_KEY")

    # Initialize database and mail, migrate
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    from . import models

    # Login manager setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(main)

    # OAuth setup for Google Login
    google_bp = make_google_blueprint(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_url="/auth/google",
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    # Error handler for file size limit
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        flash(
            "File too large. Maximum file size is 16MB. Please choose a smaller file.",
            "danger",
        )
        return redirect(url_for("main.post_item")), 413

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
