from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

favorites_table = db.Table(
    "favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("item_id", db.Integer, db.ForeignKey("items.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class RecentlyViewed(db.Model):
    __tablename__ = "recently_viewed"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    item = db.relationship("Item")
    user = db.relationship("User", backref=db.backref("viewed_history", lazy="dynamic"))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(150), nullable=True)
    last_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    profile_image = db.Column(db.String(255), nullable=True)

    favorites = db.relationship(
        "Item",
        secondary=favorites_table,
        backref=db.backref("favorited_by", lazy="dynamic"),
        lazy="dynamic",
    )

    items = db.relationship("Item", backref="seller", lazy=True)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown"

    @property
    def name(self):
        return self.full_name

    def __repr__(self):
        return f"<User {self.email}>"


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    size = db.Column(db.String(50))
    seller_type = db.Column(db.String(50))
    condition = db.Column(db.String(50))
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Item {self.title} (${self.price})>"

    @classmethod
    def search(cls, term):
        """
        Returns a SQLAlchemy query filtered by a search term (title or description).
        If no term is provided, returns the base Item.query.
        """
        if not term:
            return cls.query
        term = term.strip()
        return cls.query.filter(
            cls.title.ilike(f"%{term}%") | cls.description.ilike(f"%{term}%")
        )


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)

    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)

    pickup_time = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(255), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship("Item", backref="orders")
    buyer = db.relationship("User", backref="orders_placed", foreign_keys=[buyer_id])

    def __repr__(self):
        return f"<Order #{self.id} for item {self.item_id}>"
