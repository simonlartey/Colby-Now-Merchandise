from flask import current_app
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from app.models import User, db


def test_signup_get(client):
    resp = client.get("/auth/signup")
    assert resp.status_code == 200


def test_signup_reject_non_colby(client):
    resp = client.post(
        "/auth/signup",
        data={
            "first_name": "Ninh",
            "last_name": "Nguyen",
            "email": "ninh@gmail.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        },
        follow_redirects=True,
    )
    assert b"Colby College email" in resp.data


def test_signup_existing_user(client, app):
    # Create an existing user
    with app.app_context():
        u = User(
            email="existing@colby.edu",
            password=generate_password_hash("StrongPass123!", method="pbkdf2:sha256"),
            first_name="Ex",
            last_name="Isting",
            is_verified=True,
        )
        db.session.add(u)
        db.session.commit()

    resp = client.post(
        "/auth/signup",
        data={
            "first_name": "New",
            "last_name": "User",
            "email": "existing@colby.edu",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        },
        follow_redirects=True,
    )
    assert b"already exists" in resp.data


def test_signup_password_mismatch(client):
    resp = client.post(
        "/auth/signup",
        data={
            "first_name": "Ninh",
            "last_name": "Nguyen",
            "email": "ninh@colby.edu",
            "password": "StrongPass123!",
            "confirm_password": "OtherPass123!",
        },
        follow_redirects=True,
    )
    assert b"Passwords do not match" in resp.data


def test_signup_weak_password(client):
    resp = client.post(
        "/auth/signup",
        data={
            "first_name": "Ninh",
            "last_name": "Nguyen",
            "email": "ninhweak@colby.edu",
            "password": "weakpass",
            "confirm_password": "weakpass",
        },
        follow_redirects=True,
    )
    assert b"Password must be at least 12 characters" in resp.data


def test_signup_success_creates_user(client, app):
    email = "newuser@colby.edu"
    resp = client.post(
        "/auth/signup",
        data={
            "first_name": "New",
            "last_name": "User",
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        u = User.query.filter_by(email=email).first()
        assert u is not None
        assert u.is_verified is False


def test_login_get(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200


def test_login_empty_fields(client):
    resp = client.post(
        "/auth/login",
        data={"email": "", "password": ""},
        follow_redirects=True,
    )
    assert b"Please enter both email and password" in resp.data


def test_login_invalid_credentials_no_user(client):
    resp = client.post(
        "/auth/login",
        data={"email": "nosuch@colby.edu", "password": "whatever"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in resp.data


def test_login_wrong_password(client, create_user):
    u, _ = create_user(email="loginwrong@colby.edu")
    resp = client.post(
        "/auth/login",
        data={"email": u.email, "password": "WrongPass123!"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in resp.data


def test_login_block_unverified_user(client, app):
    with app.app_context():
        hashed = generate_password_hash("StrongPass123!", method="pbkdf2:sha256")
        u = User(
            email="unverified@colby.edu",
            password=hashed,
            first_name="Un",
            last_name="Verified",
            is_verified=False,
        )
        db.session.add(u)
        db.session.commit()

    resp = client.post(
        "/auth/login",
        data={"email": "unverified@colby.edu", "password": "StrongPass123!"},
        follow_redirects=True,
    )
    assert b"verify your email" in resp.data


def test_login_success_and_logout(client, create_user):
    u, pw = create_user(email="loginok@colby.edu")
    resp = client.post(
        "/auth/login",
        data={"email": u.email, "password": pw},
        follow_redirects=True,
    )
    assert b"Login successful" in resp.data

    resp2 = client.get("/auth/logout", follow_redirects=True)
    assert b"logged out" in resp2.data.lower()


def test_forgot_password_unknown_email(client):
    resp = client.post(
        "/auth/forgot-password",
        data={"email": "nosuch@colby.edu"},
        follow_redirects=True,
    )
    assert b"No account found" in resp.data


def test_forgot_password_sends_email(client, create_user):
    u, _ = create_user(email="resetme@colby.edu")
    resp = client.post(
        "/auth/forgot-password",
        data={"email": u.email},
        follow_redirects=True,
    )
    assert b"Password reset instructions" in resp.data


def test_reset_password_invalid_token(client):
    resp = client.get("/auth/reset-password/invalidtoken", follow_redirects=True)
    assert b"invalid or has expired" in resp.data


def test_reset_password_success_flow(client, app, create_user):
    u, _ = create_user(email="resetok@colby.edu")

    with app.app_context():
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(u.email, salt="password-reset-salt")

    resp = client.post(
        f"/auth/reset-password/{token}",
        data={
            "password": "NewStrongPass123!",
            "confirm_password": "NewStrongPass123!",
        },
        follow_redirects=True,
    )
    assert b"password has been reset" in resp.data


def test_verify_email_invalid_token(client):
    resp = client.get("/auth/verify/invalidtoken", follow_redirects=True)
    assert b"invalid or has expired" in resp.data


def test_verify_email_success(client, app):
    with app.app_context():
        u = User(
            email="verify@colby.edu",
            password="x",
            first_name="Verify",
            last_name="Me",
            is_verified=False,
        )
        db.session.add(u)
        db.session.commit()

        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(u.email, salt="email-verify-salt")

    resp = client.get(f"/auth/verify/{token}", follow_redirects=True)
    assert b"email has been verified" in resp.data

    with app.app_context():
        u2 = User.query.filter_by(email="verify@colby.edu").first()
        assert u2.is_verified is True


def test_verify_email_already_verified(client, app):
    with app.app_context():
        u = User(
            email="already@colby.edu",
            password="x",
            first_name="Al",
            last_name="Ready",
            is_verified=True,
        )
        db.session.add(u)
        db.session.commit()

        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(u.email, salt="email-verify-salt")

    resp = client.get(f"/auth/verify/{token}", follow_redirects=True)
    assert b"already verified" in resp.data


def test_google_login_redirects_when_not_authorized(client, monkeypatch):
    # Patch the google object in app.auth module correctly
    import sys

    auth_module = sys.modules["app.auth"]

    class DummyGoogle:
        @property
        def authorized(self):
            return False

        def get(self, url):
            raise AssertionError("Should not be called when not authorized")

    monkeypatch.setattr(auth_module, "google", DummyGoogle())

    resp = client.get("/auth/google", follow_redirects=False)
    assert resp.status_code in (302, 303)
    # It should redirect to google.login internally
    assert "login" in resp.headers.get("Location", "").lower()


def test_google_login_creates_and_logs_in_user(client, monkeypatch, app):
    import sys

    auth_module = sys.modules["app.auth"]

    class DummyResp:
        def json(self):
            return {
                "email": "googleuser@colby.edu",
                "name": "Google User",
            }

    class DummyGoogle:
        def __init__(self):
            self._authorized = True

        @property
        def authorized(self):
            return self._authorized

        def get(self, url):
            return DummyResp()

    monkeypatch.setattr(auth_module, "google", DummyGoogle())

    resp = client.get("/auth/google", follow_redirects=False)
    # Should redirect to /home after login
    assert resp.status_code in (302, 303)
    assert "/home" in resp.headers.get("Location", "")

    with app.app_context():
        u = User.query.filter_by(email="googleuser@colby.edu").first()
        assert u is not None
        assert u.is_verified is True


def test_signup_missing_fields(client):
    """Cover empty form submissions in signup."""
    resp = client.post("/auth/signup", data={}, follow_redirects=True)
    assert b"Please use your Colby College email address" in resp.data


def test_login_timing_protection(client):
    """Exercises the 'if not user' block that runs a dummy hash check."""
    resp = client.post(
        "/auth/login",
        data={"email": "nonexistent@colby.edu", "password": "somepassword"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in resp.data


def test_google_login_non_colby(client, monkeypatch):
    """Tests the restriction on non-Colby Google accounts."""
    import sys

    auth_module = sys.modules["app.auth"]

    class DummyGoogle:
        authorized = True

        def get(self, url):
            class Resp:
                def json(self):
                    return {"email": "stranger@gmail.com", "name": "Evil Hacker"}

            return Resp()

    monkeypatch.setattr(auth_module, "google", DummyGoogle())
    resp = client.get("/auth/google", follow_redirects=True)
    assert b"Please use your @colby.edu email address" in resp.data
