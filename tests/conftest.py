import os
import sys
from unittest.mock import MagicMock
import pytest
from flask import current_app
from werkzeug.security import generate_password_hash

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "password123!")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Mock imported libraries
sys.modules["boto3"] = MagicMock()
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.config"] = MagicMock()
sys.modules["botocore.exceptions"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

from app import create_app
from app.models import db, User, Item, Order


@pytest.fixture(scope="session")
def app():
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    """
    Globally mock generate_embedding to avoid loading SentenceTransformer.
    Returns a simple fixed vector when text is non-empty.
    """
    import sys

    # Ensure modules are loaded
    import app.utils.search_utils
    import app.models
    import app.main

    def fake_generate_embedding(text):
        if not text:
            return None
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        sys.modules["app.utils.search_utils"],
        "generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        sys.modules["app.models"], "generate_embedding", fake_generate_embedding
    )
    monkeypatch.setattr(
        sys.modules["app.main"], "generate_embedding", fake_generate_embedding
    )

    # Also mock cosine_similarity just in case
    def fake_cosine_similarity(v1, v2):
        return 1.0 if v1 == v2 else 0.0

    monkeypatch.setattr(
        sys.modules["app.utils.search_utils"],
        "cosine_similarity",
        fake_cosine_similarity,
    )
    monkeypatch.setattr(
        sys.modules["app.models"], "cosine_similarity", fake_cosine_similarity
    )


@pytest.fixture(autouse=True)
def mock_mail_send(monkeypatch, app):
    """
    Globally mock Flask-Mail send() so tests never hit real SMTP.
    """
    with app.app_context():
        mail_ext = current_app.extensions.get("mail")
        if mail_ext:

            def dummy_send(msg):
                # Could append to a list for inspection if needed
                return None

            monkeypatch.setattr(mail_ext, "send", dummy_send)
    yield


@pytest.fixture
def create_user():
    """
    Helper to create a user with a known password.
    Returns (user, plaintext_password).
    Ensures unique email if not provided.
    """
    counter = {"i": 0}

    def _create_user(
        email=None,
        password="StrongPass123!",
        is_verified=True,
        first_name="Test",
        last_name="User",
    ):
        if email is None:
            counter["i"] += 1
            email = f"user{counter['i']}@colby.edu"

        hashed = generate_password_hash(password, method="pbkdf2:sha256")
        user = User(
            email=email,
            password=hashed,
            first_name=first_name,
            last_name=last_name,
            is_verified=is_verified,
        )
        db.session.add(user)
        db.session.commit()
        return user, password

    return _create_user


@pytest.fixture
def logged_in_user(client, create_user):
    """
    Creates a verified user and logs them in via /auth/login.
    Returns the User instance.
    """
    user, pw = create_user()
    client.post(
        "/auth/login",
        data={"email": user.email, "password": pw},
        follow_redirects=True,
    )
    return user


@pytest.fixture
def seller_user(create_user):
    """
    Convenience fixture for a seller-type user.
    """
    u, pw = create_user(email="seller@colby.edu")
    return u


@pytest.fixture(autouse=True)
def cleanup(app):
    """
    Clean up the database after each test.
    """
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()


@pytest.fixture
def sample_item(seller_user):
    """
    Create a simple active item belonging to seller_user.
    """
    item = Item(
        title="Test Item",
        description="A nice test item",
        category="electronics",
        size="M",
        seller_type="student",
        condition="new",
        price=10.0,
        item_image=None,
        seller_id=seller_user.id,
        is_active=True,
        embedding=[0.1, 0.2, 0.3],
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture
def sample_order(logged_in_user, sample_item):
    """
    Create an order where logged_in_user is buyer, sample_item.seller is seller.
    """
    order = Order(
        buyer_id=logged_in_user.id,
        item_id=sample_item.id,
        location="Mule Works",
        notes="Leave at front desk",
        status="pending",
    )
    db.session.add(order)
    db.session.commit()
    return order


@pytest.fixture
def sample_chat_pair(create_user):
    """
    Create two users to be used in chat tests.
    Returns (user1, user2).
    """
    user1, _ = create_user(email="chat1@colby.edu", first_name="Chat", last_name="One")
    user2, _ = create_user(email="chat2@colby.edu", first_name="Chat", last_name="Two")
    return user1, user2
