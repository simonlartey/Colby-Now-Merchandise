from datetime import datetime

from flask import current_app
from app.models import db, User, Item, Order, RecentlyViewed
from app.utils.search_utils import cosine_similarity


def login_as(client, user, password="StrongPass123!"):
    return client.post(
        "/auth/login",
        data={"email": user.email, "password": password},
        follow_redirects=True,
    )


def test_landing_page(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_home_requires_login(client):
    resp = client.get("/home", follow_redirects=False)
    # Should redirect to login
    assert resp.status_code in (302, 303)


def test_home_logged_in(client, logged_in_user, sample_item):
    resp = client.get("/home")
    assert resp.status_code == 200
    assert b"Test Item" in resp.data


def test_post_item_get(client, logged_in_user):
    resp = client.get("/post-item")
    assert resp.status_code == 200


def test_post_item_missing_title(client, logged_in_user):
    resp = client.post(
        "/post-item",
        data={"price": "10.00"},
        follow_redirects=True,
    )
    assert b"Item name is required" in resp.data


def test_post_item_invalid_price(client, logged_in_user, app):
    # Setup: Create an item to edit
    with app.app_context():
        item = Item(
            title="Test Item for Edit",
            description="desc",
            category="misc",
            price=10.0,
            seller_id=logged_in_user.id,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Re-fetch item after commit to ensure it's not stale
    with app.app_context():
        db.session.expire_all()
        item = db.session.get(Item, item_id)

    resp = client.post(
        f"/edit_item/{item.id}",
        data={
            "title": "Edit",
            "price": "invalid",
            "description": "desc",
            "category": "misc",
            "uploaded_image_filename": "test.png",
        },
        follow_redirects=True,
    )
    assert b"Invalid price" in resp.data or b"invalid price" in resp.data.lower()


def test_post_item_success(client, logged_in_user, app):
    resp = client.post(
        "/post-item",
        data={
            "title": "Nice Jacket",
            "description": "Blue jacket",
            "category": "clothing",
            "size": "M",
            "seller_type": "student",
            "condition": "new",
            "price": "20.50",
            "uploaded_image_filename": "test.png",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Item posted successfully" in resp.data

    with app.app_context():
        item = Item.query.filter_by(title="Nice Jacket").first()
        assert item is not None
        assert item.price == 20.50
        assert item.seller_id == logged_in_user.id


def test_item_details_and_recently_viewed(client, logged_in_user, sample_item, app):
    resp = client.get(f"/item/{sample_item.id}")
    assert resp.status_code == 200

    with app.app_context():
        rv = RecentlyViewed.query.filter_by(
            user_id=logged_in_user.id, item_id=sample_item.id
        ).first()
        assert rv is not None


def test_seller_details(client, logged_in_user, sample_item):
    resp = client.get(f"/seller/{sample_item.seller_id}")
    assert resp.status_code == 200


def test_my_listings_basic(client, logged_in_user, sample_item, app):
    # Setup: Assign the logged-in user as the seller of the sample item
    with app.app_context():
        sample_item.seller_id = logged_in_user.id
        db.session.commit()

    resp = client.get("/my_listings")
    assert resp.status_code == 200
    assert b"Test Item" in resp.data


def test_my_listings_search(client, logged_in_user, app):
    # Setup: Create multiple listings for the logged-in user
    with app.app_context():
        i1 = Item(
            title="Red Shirt",
            description="Nice shirt",
            category="clothing",
            price=15.0,
            seller_id=logged_in_user.id,
        )
        i2 = Item(
            title="Blue Shoes",
            description="Shoes",
            category="clothing",
            price=30.0,
            seller_id=logged_in_user.id,
        )
        db.session.add_all([i1, i2])
        db.session.commit()

    resp = client.get("/my_listings?search=Red")
    assert resp.status_code == 200
    assert b"Red Shirt" in resp.data
    assert b"Blue Shoes" not in resp.data


def test_handle_order_approve_and_reject(client, logged_in_user, sample_item, app):
    # Setup: Assign the logged-in user as the seller and create a pending order
    with app.app_context():
        sample_item.seller_id = logged_in_user.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="Somewhere",
            status="pending",
        )
        db.session.add(order)
        db.session.commit()
        order_id = order.id

    # Approve
    resp = client.post(f"/handle_order/{order_id}/approve", follow_redirects=True)
    assert resp.status_code == 200
    assert b"approved!" in resp.data or b"Pickup approved" in resp.data

    with app.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == "approved"

    # Reject
    resp2 = client.post(f"/handle_order/{order_id}/reject", follow_redirects=True)
    assert resp2.status_code == 200
    assert b"rejected" in resp2.data

    with app.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == "rejected"


def test_handle_order_unauthorized(
    client, logged_in_user, sample_item, app, create_user
):
    # Setup: Create another user to act as the unauthorized seller
    seller, _ = create_user(email="other_seller@colby.edu")
    with app.app_context():
        sample_item.seller_id = seller.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="Somewhere",
            status="pending",
        )
        db.session.add(order)
        db.session.commit()
        order_id = order.id

    resp = client.post(f"/handle_order/{order_id}/approve", follow_redirects=True)
    assert b"not authorized" in resp.data.lower()


def test_edit_item_invalid_price(client, logged_in_user, app):
    # Setup: Create an item for the logged-in user
    with app.app_context():
        item = Item(
            title="Edit Me",
            description="desc",
            category="misc",
            price=5.0,
            seller_id=logged_in_user.id,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.post(
        f"/edit_item/{item_id}",
        data={
            "title": "Edit Me",
            "price": "bad-price",
            "description": "desc",
            "category": "misc",
            "uploaded_image_filename": "",
        },
        follow_redirects=True,
    )
    assert b"Invalid price" in resp.data or b"invalid price" in resp.data.lower()


def test_edit_item_success(client, logged_in_user, app):
    with app.app_context():
        item = Item(
            title="Old Name",
            description="Old desc",
            category="misc",
            price=5.0,
            seller_id=logged_in_user.id,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.post(
        f"/edit_item/{item_id}",
        data={
            "title": "New Name",
            "price": "12.34",
            "description": "Old desc",
            "category": "misc",
            "uploaded_image_filename": "",
        },
        follow_redirects=True,
    )
    assert (
        b"Listing updated successfully" in resp.data
        or b"updated successfully" in resp.data.lower()
    )

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.title == "New Name"
        assert item.price == 12.34


def test_delete_item(client, logged_in_user, app):
    with app.app_context():
        item = Item(
            title="Delete Me",
            description="desc",
            category="misc",
            price=5.0,
            seller_id=logged_in_user.id,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.post(f"/delete_item/{item_id}", follow_redirects=True)
    assert b"Item deleted successfully" in resp.data

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.is_deleted
 

def test_place_order_get(client, logged_in_user, sample_item):
    resp = client.get(f"/order/{sample_item.id}")
    assert resp.status_code == 200
    assert b"Test Item" in resp.data


def test_create_order_invalid_datetime(client, logged_in_user, sample_item):
    resp = client.post(
        f"/order/{sample_item.id}",
        data={
            "location": "Test Location",
            "notes": "note",
            "pickup_date": "bad-date",
            "pickup_time": "10:00",
        },
        follow_redirects=True,
    )
    assert b"Invalid pickup date or time" in resp.data


def test_create_order_success(client, logged_in_user, sample_item, app):
    resp = client.post(
        f"/order/{sample_item.id}",
        data={
            "location": "Test Location",
            "notes": "note",
            "pickup_date": "2025-01-01",
            "pickup_time": "10:00",
        },
        follow_redirects=True,
    )
    assert b"Order request sent to seller" in resp.data

    with app.app_context():
        order = Order.query.filter_by(
            buyer_id=logged_in_user.id, item_id=sample_item.id
        ).first()
        assert order is not None
        assert order.status == "pending"
        assert order.location == "Test Location"


def test_my_orders_grouping(client, logged_in_user, sample_item, app):
    with app.app_context():
        # create a few orders with different statuses
        o1 = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="pending",
        )
        o2 = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="approved",
        )
        o3 = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="completed",
        )
        db.session.add_all([o1, o2, o3])
        db.session.commit()

    resp = client.get("/my_orders")
    assert resp.status_code == 200
    assert b"pending" in resp.data.lower()
    assert b"approved" in resp.data.lower()
    assert b"completed" in resp.data.lower()


def test_confirm_order_authorized(client, logged_in_user, sample_item, app):
    with app.app_context():
        o = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="approved",
        )
        db.session.add(o)
        db.session.commit()
        oid = o.id

    resp = client.post(f"/confirm_order/{oid}")
    assert resp.status_code == 200
    assert resp.is_json
    assert resp.json["success"] is True


def test_favorites_add_and_remove(client, logged_in_user, sample_item, app):
    # Add favorite
    resp = client.post(f"/favorites/add/{sample_item.id}", follow_redirects=True)
    assert b"Added to favorites" in resp.data

    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        item = db.session.get(Item, sample_item.id)
        assert item in user.favorites.all()

    # Remove favorite
    resp2 = client.get(f"/favorites/remove/{sample_item.id}", follow_redirects=True)
    assert b"Removed from favorites" in resp2.data

    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        item = db.session.get(Item, sample_item.id)
        assert item not in user.favorites.all()


def test_favorites_page(client, logged_in_user, sample_item, app):
    # ensure the item is favorited
    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        item = db.session.get(Item, sample_item.id)
        user.favorites.append(item)
        db.session.commit()

    resp = client.get("/favorites")
    assert resp.status_code == 200
    assert b"Test Item" in resp.data


def test_autocomplete(client, logged_in_user, app):
    with app.app_context():
        item = Item(
            title="Autocomplete Item",
            description="stuff",
            category="misc",
            price=1.0,
            seller_id=logged_in_user.id,
        )
        db.session.add(item)
        db.session.commit()
        iid = item.id

    resp = client.get("/autocomplete?q=Auto")
    assert resp.status_code == 200
    assert resp.is_json
    assert any(entry["id"] == iid for entry in resp.json)


def test_contact_us_get(client):
    resp = client.get("/contact_us")
    assert resp.status_code == 200


def test_contact_us_post(client):
    resp = client.post(
        "/contact_us",
        data={
            "first_name": "Ninh",
            "last_name": "Nguyen",
            "email": "ninh@example.com",
            "message": "Hello there",
            "affiliation": "Student",
            "phone_number": "123456",
        },
        follow_redirects=True,
    )
    assert b"Your message has been received" in resp.data


def test_profile(client, logged_in_user, app, sample_item):
    # Setup: Populate user profile with favorites, orders, and view history
    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        item = db.session.get(Item, sample_item.id)
        user.favorites.append(item)
        db.session.commit()

        order = Order(
            buyer_id=user.id,
            item_id=item.id,
            location="loc",
            status="pending",
        )
        db.session.add(order)
        rv = RecentlyViewed(user_id=user.id, item_id=item.id)
        db.session.add(rv)
        db.session.commit()

    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"Test Item" in resp.data


def test_update_profile(client, logged_in_user, app):
    resp = client.post(
        "/update_profile",
        data={"first_name": "NewFN", "last_name": "NewLN"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        assert user.first_name == "NewFN"
        assert user.last_name == "NewLN"


def test_approve_pickup_authorized(client, logged_in_user, sample_item, app):
    with app.app_context():
        # Make logged_in_user the seller
        sample_item.seller_id = logged_in_user.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="pending",
        )
        db.session.add(order)
        db.session.commit()
        oid = order.id

    resp = client.post(f"/approve_pickup/{oid}", follow_redirects=True)
    assert b"Pickup approved" in resp.data

    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.status == "approved"
        assert order.item.is_active is False


def test_approve_pickup_unauthorized(
    client, logged_in_user, sample_item, app, create_user
):
    # Setup: Assign a different user as the item seller
    seller, _ = create_user(email="other_seller2@colby.edu")
    with app.app_context():
        sample_item.seller_id = seller.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="pending",
        )
        db.session.add(order)
        db.session.commit()
        oid = order.id

    resp = client.post(f"/approve_pickup/{oid}", follow_redirects=True)
    assert b"not allowed to approve" in resp.data.lower()


def test_mark_sold_authorized(client, logged_in_user, sample_item, app):
    with app.app_context():
        sample_item.seller_id = logged_in_user.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="approved",
        )
        db.session.add(order)
        db.session.commit()
        oid = order.id

    resp = client.post(f"/mark_sold/{oid}")
    assert resp.status_code == 200
    assert resp.is_json
    assert resp.json["success"] is True

    with app.app_context():
        order = db.session.get(Order, oid)
        assert order.status == "completed"


def test_mark_sold_wrong_status(client, logged_in_user, sample_item, app):
    with app.app_context():
        sample_item.seller_id = logged_in_user.id
        order = Order(
            buyer_id=logged_in_user.id,
            item_id=sample_item.id,
            location="loc",
            status="pending",  # not approved
        )
        db.session.add(order)
        db.session.commit()
        oid = order.id

    resp = client.post(f"/mark_sold/{oid}")
    assert resp.status_code == 200
    assert resp.json["success"] is False


def test_user_item_order_repr(app, logged_in_user, sample_item):
    with app.app_context():
        user = db.session.get(User, logged_in_user.id)
        item = db.session.get(Item, sample_item.id)
        order = Order(
            buyer_id=user.id,
            item_id=item.id,
            location="loc",
            status="pending",
        )
        db.session.add(order)
        db.session.commit()

        assert "User" in repr(user)
        assert "Item" in repr(item)
        assert "Order" in repr(order)


def test_item_search_and_semantic_search(app, logged_in_user):
    with app.app_context():
        i1 = Item(
            title="Blue Jacket",
            description="warm jacket",
            category="clothing",
            price=30.0,
            seller_id=logged_in_user.id,
            is_active=True,
            embedding=[0.1, 0.2, 0.3],
        )
        i2 = Item(
            title="Red Hat",
            description="small hat",
            category="clothing",
            price=10.0,
            seller_id=logged_in_user.id,
            is_active=True,
            embedding=[0.1, 0.2, 0.3],
        )
        db.session.add_all([i1, i2])
        db.session.commit()

        # Re-fetch items within the context to ensure they are available
        i1 = db.session.get(Item, i1.id)
        i2 = db.session.get(Item, i2.id)

        # search() no term returns base query
        q = Item.search("")
        assert q.count() >= 2

        # search with term
        q2 = Item.search("Jacket")
        results = q2.all()
        assert any("Jacket" in item.title for item in results)

        # semantic_search no term returns most recent
        sem_all = Item.semantic_search("", limit=1)
        assert len(sem_all) == 1
        # Verify semantic search with a term
        sem = Item.semantic_search("warm jacket", limit=5)
        assert len(sem) > 0
        assert any("Jacket" in item.title for item in sem)


def test_cosine_similarity_basic():
    v1 = [1, 0]
    v2 = [1, 0]
    v3 = [0, 1]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6
    assert abs(cosine_similarity(v1, v3)) < 1e-6
    assert cosine_similarity(None, v2) == 0.0
    assert cosine_similarity(v1, None) == 0.0
    assert cosine_similarity([0, 0], [1, 2]) == 0.0


def test_approve_pickup_already_approved(client, logged_in_user, sample_item, app):
    """
    Covers the 'if order.status != pending' branch in main.approve_pickup.
    Ensures that an order already in 'approved' status cannot be approved again.
    """
    with app.app_context():
        sample_item.seller_id = logged_in_user.id
        order = Order(
            buyer_id=999,
            item_id=sample_item.id,
            location="Miller Library",
            status="approved",
        )
        db.session.add(order)
        db.session.commit()
        oid = order.id

    resp = client.post(f"/approve_pickup/{oid}", follow_redirects=True)

    assert b"This order cannot be approved" in resp.data
