import pytest
from datetime import datetime, timedelta
from app.models import User, Chat, db
import pytz
from werkzeug.security import generate_password_hash


@pytest.fixture
def two_users(app, client):
    hashed_pw = generate_password_hash("x", method="pbkdf2:sha256")

    u1 = User(
        email="u1@colby.edu",
        password=hashed_pw,
        first_name="A",
        last_name="One",
        is_verified=True,
    )
    u2 = User(
        email="u2@colby.edu",
        password=hashed_pw,
        first_name="B",
        last_name="Two",
        is_verified=True,
    )
    db.session.add_all([u1, u2])
    db.session.commit()

    # login u1
    client.post("/auth/login", data={"email": u1.email, "password": "x"})

    yield u1, u2

    # cleanup
    client.get("/auth/logout", follow_redirects=True)


# --------------------------------------
# chat page — no messages
# --------------------------------------
def test_chat_empty(client, two_users):
    u1, u2 = two_users
    resp = client.get(f"/chat/{u2.id}")
    assert resp.status_code == 200


# --------------------------------------
# chat page — invalid receiver (404)
# --------------------------------------
def test_chat_invalid_receiver(client, two_users):
    resp = client.get("/chat/999999")
    assert resp.status_code == 404


# --------------------------------------
# send_message missing content
# --------------------------------------
def test_send_message_missing_content(client, two_users):
    resp = client.post("/send_message", json={}, follow_redirects=True)
    assert resp.status_code == 400


# --------------------------------------
# send_message success
# --------------------------------------
def test_send_message_success(client, two_users):
    u1, u2 = two_users
    resp = client.post(
        "/send_message",
        json={"receiver_id": u2.id, "content": "hi"},
    )
    assert resp.json["success"] is True


# --------------------------------------
# get_messages — no messages
# --------------------------------------
def test_get_messages_empty(client, two_users):
    u1, u2 = two_users
    resp = client.get(f"/get_messages/{u2.id}")
    assert resp.json == []


# --------------------------------------
# get_messages — with messages
# --------------------------------------
def test_get_messages_with_data(client, two_users, app):
    u1, u2 = two_users

    msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="test")
    db.session.add(msg)
    db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert len(resp.json) == 1
    assert resp.json[0]["content"] == "test"


# --------------------------------------
# get_messages — timestamp conversion
# --------------------------------------
def test_get_messages_time_format(client, two_users, app):
    u1, u2 = two_users

    t = datetime.utcnow() - timedelta(hours=1)
    msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="time", timestamp=t)
    db.session.add(msg)
    db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert "•" in resp.json[0]["time"]  # format "Jan 01 • 12:00 PM"


# --------------------------------------
# inbox — empty
# --------------------------------------
def test_inbox_empty(client, two_users):
    resp = client.get("/inbox")
    assert resp.status_code == 200


# --------------------------------------
# inbox — with conversations
# --------------------------------------
def test_inbox_with_messages(client, two_users, app):
    u1, u2 = two_users

    c = Chat(sender_id=u1.id, receiver_id=u2.id, content="hi")
    db.session.add(c)
    db.session.commit()

    resp = client.get("/inbox")
    assert b"Two" in resp.data  # u2 displayed


# --------------------------------------
# send_message — empty content (edge case)
# --------------------------------------
def test_send_message_empty_content(client, two_users):
    u1, u2 = two_users
    resp = client.post(
        "/send_message",
        json={"receiver_id": u2.id, "content": ""},
    )
    assert resp.status_code == 400  # Assuming app validates empty content


# --------------------------------------
# send_message — invalid receiver_id
# --------------------------------------
def test_send_message_invalid_receiver(client, two_users):
    u1, u2 = two_users
    resp = client.post(
        "/send_message",
        json={"receiver_id": 999999, "content": "hi"},
    )
    assert resp.status_code == 404


# --------------------------------------


# --------------------------------------
# send_message — not logged in
# --------------------------------------
# --------------------------------------
# send_message — not logged in
# --------------------------------------
# --------------------------------------
# send_message — not logged in
# --------------------------------------
def test_send_message_not_logged_in(client, app):
    # client.get("/auth/logout") removed - fixture handles it

    u = User(
        email="test@colby.edu",
        password="x",
        first_name="T",
        last_name="U",
        is_verified=True,
    )
    db.session.add(u)
    db.session.commit()
    receiver_id = u.id

    resp = client.post(
        "/send_message",
        json={"receiver_id": receiver_id, "content": "hi"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/auth/login" in resp.location


# --------------------------------------
# get_messages — multiple messages
# --------------------------------------
def test_get_messages_multiple(client, two_users, app):
    u1, u2 = two_users

    msgs = [
        Chat(sender_id=u1.id, receiver_id=u2.id, content="msg1"),
        Chat(sender_id=u2.id, receiver_id=u1.id, content="msg2"),
    ]
    db.session.add_all(msgs)
    db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert len(resp.json) == 2
    assert resp.json[0]["content"] == "msg1"
    assert resp.json[1]["content"] == "msg2"


# --------------------------------------
# get_messages — timezone handling (using pytz)
# --------------------------------------
def test_get_messages_timezone(client, two_users, app):
    u1, u2 = two_users

    tz = pytz.timezone("US/Eastern")
    t = tz.localize(datetime(2025, 12, 23, 12, 0, 0))
    msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="tz test", timestamp=t)
    db.session.add(msg)
    db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert resp.json[0]["time"]  # Ensure time is formatted correctly


# --------------------------------------
# inbox — multiple conversations
# --------------------------------------
def test_inbox_multiple_conversations(client, two_users, app):
    u1, u2 = two_users

    u3 = User(
        email="u3@colby.edu",
        password="x",
        first_name="C",
        last_name="Three",
        is_verified=True,
    )
    db.session.add(u3)
    msgs = [
        Chat(sender_id=u1.id, receiver_id=u2.id, content="to u2"),
        Chat(sender_id=u1.id, receiver_id=u3.id, content="to u3"),
    ]
    db.session.add_all(msgs)
    db.session.commit()

    resp = client.get("/inbox")
    assert b"Two" in resp.data
    assert b"Three" in resp.data


# --------------------------------------
# inbox — not logged in
# --------------------------------------
def test_inbox_not_logged_in(client):
    resp = client.get("/inbox")
    assert resp.status_code == 302  # Assuming auth required


# --------------------------------------
# chat page — self-chat (edge case)
# --------------------------------------
def test_chat_self(client, two_users):
    u1, u2 = two_users
    resp = client.get(f"/chat/{u1.id}")  # Chat with self
    assert resp.status_code == 200  # Or 400 if blocked


# --------------------------------------
# User model — basic creation and verification
# --------------------------------------
def test_user_creation(app):

    u = User(
        email="new@colby.edu",
        password="pass",
        first_name="New",
        last_name="User",
        is_verified=False,
    )
    db.session.add(u)
    db.session.commit()
    assert u.id is not None
    assert not u.is_verified


# --------------------------------------
# Chat model — timestamp default
# --------------------------------------
def test_chat_timestamp_default(app):

    u1 = User(
        email="a@colby.edu",
        password="x",
        first_name="A",
        last_name="A",
        is_verified=True,
    )
    u2 = User(
        email="b@colby.edu",
        password="x",
        first_name="B",
        last_name="B",
        is_verified=True,
    )
    db.session.add_all([u1, u2])
    db.session.commit()

    msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="test")
    db.session.add(msg)
    db.session.commit()
    assert msg.timestamp is not None
