from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import current_app
from datetime import datetime
import pickle
from .search_utils import generate_embedding, cosine_similarity

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

    messages_sent = db.relationship(
        "Chat", foreign_keys="Chat.sender_id", backref="sender", lazy="dynamic"
    )

    messages_received = db.relationship(
        "Chat", foreign_keys="Chat.receiver_id", backref="receiver", lazy="dynamic"
    )

    @property
    def profile_image_url(self):
        """
        Generates a presigned URL for making GET requests to retrieving the current user's profile picture from a cloud storage bucket.
        If user has no profile image, fall back to default profile picture.
        """
        if self.profile_image:
            try:
                image_url = current_app.s3_client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": current_app.s3_bucket_id,
                        "Key": self.profile_image,
                    },
                    ExpiresIn=3600,
                )
                return image_url
            except Exception as e:
                current_app.logger.error(f"Error generating presigned URL: {e}")
                return url_for("static", filename="images/default_user_profile.png")
        else:
            return url_for("static", filename="images/default_user_profile.png")


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
    item_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    embedding = db.Column(
        db.PickleType, nullable=True
    )  # Stores numpy array of embedding

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

    @classmethod
    def semantic_search(cls, term, limit=20, threshold=0.25):
        """
        Performs a semantic search using cosine similarity on embeddings.
        Fallback to standard search if no term provided.
        Returns a list of Items (not a query object).
        """
        if not term:
            return (
                cls.query.filter_by(is_active=True)
                .order_by(cls.created_at.desc())
                .limit(limit)
                .all()
            )

        # 1. Generate query embedding
        query_emb = generate_embedding(term)
        if query_emb is None:
            return []

        # 2. Fetch all active items with embeddings
        # NOTE: This loads all active item embeddings into memory.
        # OK for <10k items.
        items = cls.query.filter(cls.is_active == True).all()
        items = [item for item in items if item.embedding is not None]

        if not items:
            return []

        # 3. Calculate similarities
        scored_items = []
        for item in items:
            score = cosine_similarity(query_emb, item.embedding)
            if score >= threshold:
                scored_items.append((score, item))

        # 4. Sort by score (descending)
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # 5. Return top N items
        return [item for score, item in scored_items[:limit]]

    @property
    def item_image_url(self):
        """
        Generates a presigned URL for making GET requests to retrieve an image of this item.
        Falls back to default item image if item image URL could not be generated.
        """
        if self.item_image:
            try:
                image_url = current_app.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": current_app.s3_bucket_id, "Key": self.item_image},
                    ExpiresIn=3600,
                )
                return image_url
            except:
                return url_for("static", filename="images/default_item.png")
        else:
            return url_for("static", filename="images/default_item.png")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)

    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)

    pickup_time = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship("Item", backref="orders")
    buyer = db.relationship("User", backref="orders_placed", foreign_keys=[buyer_id])

    def __repr__(self):
        return f"<Order #{self.id} for item {self.item_id}>"


class Chat(db.Model):
    __tablename__ = "chat"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
