from flask import Flask, redirect, url_for, flash
from flask_login import LoginManager
from flask_mail import Mail
from .models import db, User
from .auth import auth
from .main import main
import os
from werkzeug.exceptions import RequestEntityTooLarge


# Create a Mail instance globally
mail = Mail()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Basic app configuration
    app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max uploaded file size

    # Mail configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")  # add to .env
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")  # add to .env

    # Initialize database and mail
    db.init_app(app)
    mail.init_app(app)

    # Login manager setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(main)

    # Create tables if missing
    with app.app_context():
        db.create_all()

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
