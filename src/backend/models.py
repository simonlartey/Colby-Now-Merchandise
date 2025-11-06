from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the database instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        """Hash the password before saving."""
        self.password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.email}>'
