from app.models import db, Chat, User


def test_chat_marks_messages_read(client, app, create_user):
    # create two users
    sender, _ = create_user(email="sender@colby.edu")
    receiver, pw = create_user(email="receiver@colby.edu")

    # log in as receiver
    client.post(
        "/auth/login",
        data={"email": receiver.email, "password": pw},
        follow_redirects=True,
    )

    # create unread message from sender -> receiver
    with app.app_context():
        msg = Chat(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content="Hello",
            is_read=False,
        )
        db.session.add(msg)
        db.session.commit()
        mid = msg.id

    # visit chat
    resp = client.get(f"/chat/{sender.id}")
    assert resp.status_code == 200

    # message should now be marked as read
    with app.app_context():
        msg = Chat.query.get(mid)
        assert msg.is_read is True


def test_send_message_creates_chat_record(client, app, create_user):
    u1, pw1 = create_user(email="u1@colby.edu")
    u2, _ = create_user(email="u2@colby.edu")

    # login as u1
    client.post(
        "/auth/login",
        data={"email": u1.email, "password": pw1},
        follow_redirects=True,
    )

    resp = client.post(
        "/send_message",
        json={"receiver_id": u2.id, "content": "Hi there"},
    )
    assert resp.status_code == 200
    assert resp.is_json
    assert resp.json["success"] is True

    with app.app_context():
        msgs = Chat.query.filter_by(sender_id=u1.id, receiver_id=u2.id).all()
        assert len(msgs) == 1
        assert msgs[0].content == "Hi there"


def test_send_message_bad_request(client, create_user):
    u1, pw1 = create_user(email="u_send@colby.edu")

    client.post(
        "/auth/login",
        data={"email": u1.email, "password": pw1},
        follow_redirects=True,
    )

    resp = client.post("/send_message", json={})
    assert resp.status_code == 400


def test_get_messages_returns_conversation(client, app, create_user):
    u1, pw1 = create_user(email="c1@colby.edu")
    u2, _ = create_user(email="c2@colby.edu")

    # login as u1
    client.post(
        "/auth/login",
        data={"email": u1.email, "password": pw1},
        follow_redirects=True,
    )

    with app.app_context():
        m1 = Chat(
            sender_id=u1.id,
            receiver_id=u2.id,
            content="hello",
        )
        m2 = Chat(
            sender_id=u2.id,
            receiver_id=u1.id,
            content="hi back",
        )
        db.session.add_all([m1, m2])
        db.session.commit()

    resp = client.get(f"/get_messages/{u2.id}")
    assert resp.status_code == 200
    assert resp.is_json
    assert len(resp.json) == 2
    assert {m["content"] for m in resp.json} == {"hello", "hi back"}
    # ensure time field exists
    assert "time" in resp.json[0]


def test_inbox_lists_conversations(client, app, create_user):
    u1, pw1 = create_user(email="inbox1@colby.edu", first_name="Inbox", last_name="One")
    u2, _ = create_user(email="inbox2@colby.edu", first_name="Inbox", last_name="Two")

    # login as u1
    client.post(
        "/auth/login",
        data={"email": u1.email, "password": pw1},
        follow_redirects=True,
    )

    # create a chat from u1 to u2
    with app.app_context():
        msg = Chat(sender_id=u1.id, receiver_id=u2.id, content="hello inbox")
        db.session.add(msg)
        db.session.commit()

    resp = client.get("/inbox")
    assert resp.status_code == 200
    # Should show some reference to user 2's name
    assert b"Inbox Two" in resp.data
