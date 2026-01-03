from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify,
    abort,
)

from flask_login import login_required, current_user
from .models import Item, db, User, Order, Chat, RecentlyViewed
from sqlalchemy import or_
import pytz
from app.utils.search_utils import generate_embedding
from datetime import datetime, timezone
from flask_mail import Message

# Create a new blueprint for main pages
main = Blueprint("main", __name__)


@main.route("/")
def landing():
    """
    Displays the landing page (dashboard).
    """
    return render_template("landing.html")


@main.route("/home")
@login_required
def home():
    """
    Displays the homepage after a successful login or signup.
    Supports searching for items by keyword.
    """
    # Default homepage
    categories = ["electronics", "clothing", "furniture", "books", "miscellaneous"]

    category_items = [
        Item.query.filter_by(category=category, is_active=True, is_deleted=False)
        .order_by(Item.created_at.desc())
        .first()
        for category in categories
    ]

    category_items = [item for item in category_items if item]

    recent_items = (
        Item.query.filter_by(is_active=True)
        .order_by(Item.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "home.html",
        user=current_user,
        category_items=category_items,
        recent_items=recent_items,
    )


@main.route("/buy_item")
@login_required
def buy_item():
    categories_selected = request.args.getlist("category")
    seller_types_selected = request.args.getlist("seller_type")
    conditions_selected = request.args.getlist("condition")
    search = request.args.get("search", type=str)
    sort_by = request.args.get("sort_by", default="newest", type=str)

    query = Item.query.filter_by(is_active=True, is_deleted=False)

    if search:
        semantic_results = Item.semantic_search(search, limit=50)
        if not semantic_results:
            query = query.filter(db.false())
        else:
            relevant_ids = [item.id for item in semantic_results]
            query = query.filter(Item.id.in_(relevant_ids))

    if categories_selected:
        query = query.filter(Item.category.in_(categories_selected))
    if seller_types_selected:
        query = query.filter(Item.seller_type.in_(seller_types_selected))
    if conditions_selected:
        query = query.filter(Item.condition.in_(conditions_selected))

    if sort_by == "newest":
        query = query.order_by(Item.created_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(Item.created_at.asc())
    elif sort_by == "price_low":
        query = query.order_by(Item.price.asc())
    elif sort_by == "price_high":
        query = query.order_by(Item.price.desc())
    else:
        query = query.order_by(Item.created_at.desc())

    items = query.all()

    categories = [
        c[0] for c in db.session.query(Item.category).distinct().all() if c[0]
    ]
    seller_types = [
        s[0] for s in db.session.query(Item.seller_type).distinct().all() if s[0]
    ]
    conditions = [
        c[0] for c in db.session.query(Item.condition).distinct().all() if c[0]
    ]

    favorite_ids = [fav.id for fav in current_user.favorites]

    return render_template(
        "buy_item.html",
        items=items,
        categories=categories,
        seller_types=seller_types,
        conditions=conditions,
        categories_selected=categories_selected,
        seller_types_selected=seller_types_selected,
        conditions_selected=conditions_selected,
        current_search=search,
        current_sort=sort_by,
        item_count=len(items),
        favorite_ids=favorite_ids,
    )


@main.route("/post-item", methods=["GET", "POST"])
@login_required
def post_item():
    """
    Allows authenticated users to post a new item for sale.
    """
    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            size = request.form.get("size", "").strip()
            seller_type = request.form.get("seller_type", "").strip()
            condition = request.form.get("condition", "").strip()
            price_str = request.form.get("price", "").strip()
            uploaded_image_filename = request.form.get(
                "uploaded_image_filename", ""
            ).strip()

            if not title:
                flash("Item name is required.", "danger")
                return redirect(url_for("main.post_item"))

            if not price_str:
                flash("Price is required.", "danger")
                return redirect(url_for("main.post_item"))

            if not uploaded_image_filename:
                flash("There was an error uploading your item image file.", "danger")
                return redirect(url_for("main.post_item"))

            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                price = float(price_clean)
                if price < 0:
                    raise ValueError("Price must be positive")
            except ValueError:
                flash("Invalid price. Please enter a valid number.", "danger")
                return redirect(url_for("main.post_item"))

            new_item = Item(
                title=title,
                description=description if description else None,
                category=category if category else None,
                size=size if size else None,
                seller_type=seller_type if seller_type else None,
                condition=condition if condition else None,
                price=price,
                item_image=uploaded_image_filename,
                seller_id=current_user.id,
                embedding=generate_embedding(f"{title} {description}"),
            )

            db.session.add(new_item)
            db.session.commit()

            flash("Item posted successfully!", "success")
            return redirect(url_for("main.buy_item"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error posting item: {str(e)}", "danger")
            return redirect(url_for("main.post_item"))

    return render_template("post_new_item.html")


@main.route("/item/<int:item_id>")
@login_required
def item_details(item_id):
    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash(message="Item not found", category="danger")
        return redirect(url_for("main.buy_item"))

    if not item.is_active and current_user.id != item.seller_id:
        flash(message="Item not found", category="danger")
        return redirect(url_for("main.buy_item"))

    # --- Recently Viewed (Upsert Logic) ---
    if current_user.is_authenticated:
        existing_view = RecentlyViewed.query.filter_by(
            user_id=current_user.id, item_id=item.id
        ).first()

        if existing_view:
            existing_view.viewed_at = datetime.now(tz=timezone.utc)
        else:
            new_view = RecentlyViewed(user_id=current_user.id, item_id=item.id)
            db.session.add(new_view)

        db.session.commit()

    return render_template("item_details.html", item=item)


@main.route("/seller/<int:seller_id>")
@login_required
def seller_details(seller_id):
    """
    Displays detailed information about a specific seller.
    """
    seller = User.query.get_or_404(seller_id)
    return render_template("sellers_details.html", seller=seller)


@main.route("/my_listings")
@login_required
def my_listings():

    search = request.args.get("search", "").strip()

    # Filter items posted by current seller
    query = Item.query.filter_by(seller_id=current_user.id, is_deleted=False)

    # Apply multi-term search
    if search:
        search_terms = search.split()
        for term in search_terms:
            query = query.filter(Item.title.ilike(f"%{term}%"))

    items = query.all()

    # Orders for this seller
    incoming_orders = (
        Order.query.join(Item)
        .filter(Item.seller_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    pending_orders = [o for o in incoming_orders if o.status == "pending"]
    approved_orders = [o for o in incoming_orders if o.status == "approved"]
    completed_orders = [o for o in incoming_orders if o.status == "completed"]
    cancelled_orders = [o for o in incoming_orders if o.status == "cancelled"]

    return render_template(
        "my_listings.html",
        items=items,
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        current_search=search,
    )


@main.route("/handle_order/<int:order_id>/<action>", methods=["POST"])
@login_required
def handle_order(order_id, action):
    """Approve or Reject an order."""
    order = Order.query.get_or_404(order_id)

    # Security check: Ensure current user is the seller of the item
    if order.item.seller_id != current_user.id:
        flash("You are not authorized to manage this order.", "danger")
        return redirect(url_for("main.my_listings"))

    if action == "approve":
        order.status = "approved"
        flash(f"Order for {order.item.title} approved!", "success")
    elif action == "reject":
        order.status = "rejected"
        flash(f"Order for {order.item.title} rejected.", "secondary")

    db.session.commit()
    return redirect(url_for("main.my_listings"))


@main.route("/edit_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash("Item not found.")
        return redirect(url_for("main.my_listings"))

    if item.seller_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("main.my_listings"))

    if request.method == "POST":
        try:

            def get_stripped(key, default):
                val = request.form.get(key, default)
                return val.strip() if val else val

            item.title = get_stripped("title", item.title)
            item.description = get_stripped("description", item.description)
            item.category = get_stripped("category", item.category)
            item.size = get_stripped("size", item.size)
            item.seller_type = get_stripped("seller_type", item.seller_type)
            item.condition = get_stripped("condition", item.condition)
            price_str = request.form.get("price", str(item.price))
            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                item.price = float(price_clean)
            except ValueError:
                flash("Invalid price. Please enter a valid number.", "danger")
                return redirect(url_for("main.edit_item", item_id=item.id))

            # Update embedding
            item.embedding = generate_embedding(f"{item.title} {item.description}")

            uploaded_image_filename = request.form.get("uploaded_image_filename")

            if uploaded_image_filename != "":
                old_item_image = item.item_image
                if old_item_image:
                    current_app.s3_client.delete_object(
                        Bucket=current_app.s3_bucket_id, Key=old_item_image
                    )
                item.item_image = uploaded_image_filename

            db.session.commit()
            flash("Listing updated successfully!", "success")
            return redirect(url_for("main.my_listings"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating item: {str(e)}", "danger")
            return redirect(url_for("main.edit_item", item_id=item.id))

    return render_template("edit_item.html", item=item)


@main.route("/delete_item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)

    if item.seller_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("main.my_listings"))

    active_orders = Order.query.filter(
        Order.item_id == item_id, Order.status.in_(["pending", "approved"])
    ).all()

    if active_orders:
        flash("Item is involved in an active order and cannot be deleted")
        return redirect(url_for("main.my_listings"))

    try:
        item.is_deleted = True
        item.is_active = False
        db.session.commit()
        flash("Item deleted successfully.", "success")
    except Exception:
        current_app.logger.exception("Error deleting item")
        db.session.rollback()
        flash("There was an error deleting the item. Please try again later.")

    return redirect(url_for("main.my_listings"))


@main.route("/order/<int:item_id>", methods=["GET"])
@login_required
def place_order(item_id):
    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash("Item not found")
        return redirect(url_for("main.buy_item"))

    return render_template("order_page.html", item=item)


@main.route("/order/<int:item_id>", methods=["POST"])
@login_required
def create_order(item_id):

    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash("Item not found")
        return redirect(url_for("main.buy_item"))

    # Get form fields
    location = request.form.get("location")
    notes = request.form.get("notes")

    # pickup date + time
    pickup_date = request.form.get("pickup_date")
    pickup_time = request.form.get("pickup_time")

    # Convert date + time to a single datetime
    combined_pickup_time = None
    if pickup_date and pickup_time:
        try:
            combined_pickup_time = datetime.strptime(
                f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            flash("Invalid pickup date or time.", "danger")
            return redirect(url_for("main.place_order", item_id=item_id))

    # Create the order
    order = Order(
        buyer_id=current_user.id,
        item_id=item_id,
        location=location,
        notes=notes,
        pickup_time=combined_pickup_time,
        status="pending",
    )

    db.session.add(order)
    db.session.commit()

    flash("Order request sent to seller!", "success")
    return redirect(url_for("main.my_orders"))


@main.route("/my_orders")
@login_required
def my_orders():
    search = request.args.get("search", "").strip()

    # Base query
    query = Order.query.join(Item).filter(Order.buyer_id == current_user.id)

    # Multi-word search
    if search:
        search_terms = search.split()
        for term in search_terms:
            query = query.filter(Item.title.ilike(f"%{term}%"))

    orders = query.order_by(Order.created_at.desc()).all()

    # Group orders
    pending_orders = [o for o in orders if o.status == "pending"]
    approved_orders = [o for o in orders if o.status == "approved"]
    completed_orders = [o for o in orders if o.status == "completed"]
    cancelled_orders = [o for o in orders if o.status == "cancelled"]

    return render_template(
        "my_orders.html",
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        current_search=search,
    )


@main.route("/confirm_order/<int:order_id>", methods=["POST"])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    order.status = "completed"
    db.session.commit()
    return jsonify({"success": True})


@main.route("/favorites")
@login_required
def favorites():
    fav_items = (
        current_user.favorites.filter_by(is_deleted=False).all()
        if hasattr(current_user.favorites, "all")
        else [item for item in current_user.favorites if not item.is_deleted]
    )
    return render_template("favorites.html", favorites=fav_items)


@main.route("/favorites/add/<int:item_id>", methods=["POST"])
@login_required
def add_favorite(item_id):
    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash("Item not found")
        return redirect(url_for("main.favorites"))

    if not current_user.favorites.filter_by(id=item.id).first():
        current_user.favorites.append(item)
        db.session.commit()
        flash("Added to favorites", "success")

    return redirect(request.referrer or url_for("main.favorites"))


@main.route("/favorites/remove/<int:item_id>")
@login_required
def remove_favorite(item_id):
    item = Item.query.filter_by(id=item_id, is_deleted=False).first()

    if not item:
        flash("Item not found")
        return redirect(url_for("main.favorites"))

    if current_user.favorites.filter_by(id=item.id).first():
        current_user.favorites.remove(item)
        db.session.commit()
        flash("Removed from favorites", "success")

    return redirect(request.referrer or url_for("main.favorites"))


@main.route("/autocomplete")
@login_required
def autocomplete():
    """
    Returns JSON search suggestions for live autocomplete.
    """
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    # Get up to 8 matching items
    items = (
        Item.query.filter_by(is_deleted=False)
        .filter(Item.title.ilike(f"%{query}%"))
        .order_by(Item.created_at.desc())
        .limit(8)
        .all()
    )

    results = []
    for item in items:
        results.append(
            {"id": item.id, "title": item.title, "image": item.item_image_url}
        )

    return jsonify(results)


@main.route("/contact_us", methods=["GET", "POST"])
def contact_us():
    """
    Displays the contact us page and handles form submissions.
    """
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        message = request.form.get("message")
        affiliation = request.form.get("affiliation")
        phone_number = request.form.get("phone_number")

        # Email the support team
        msg = Message(
            subject="New Contact Form Submission",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[current_app.config["MAIL_USERNAME"]],
            body=f"""
You have received a new message from the contact form:

    Name: {first_name} {last_name}
    Email: {email}
    Phone: {phone_number}
    Affiliation: {affiliation}

    Message:
    {message}
""",
        )

        try:
            current_app.extensions["mail"].send(msg)
            flash(
                f"Thank you, {first_name}! Your message has been received.", "success"
            )
        except Exception as e:
            flash(f"Error sending message: {str(e)}", "danger")

        return redirect(url_for("main.contact_us"))

    return render_template("contact_us.html")


@main.route("/chat/<int:receiver_id>")
@login_required
def chat(receiver_id):
    seller = User.query.get_or_404(receiver_id)

    Chat.query.filter_by(
        sender_id=receiver_id, receiver_id=current_user.id, is_read=False
    ).update({"is_read": True})

    db.session.commit()

    return render_template("chat.html", receiver_id=receiver_id, receiver=seller)


@main.route("/send_message", methods=["POST"])
@login_required
def send_message():
    data = request.get_json()

    if not data or not data.get("content"):
        return jsonify({"success": False}), 400

    receiver_id = data.get("receiver_id")
    if not receiver_id:
        return jsonify({"success": False}), 400

    # Validate receiver exists
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"error": "Receiver not found"}), 404

    msg = Chat(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=data["content"],
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({"success": True})


@main.route("/get_messages/<int:user_id>")
@login_required
def get_messages(user_id):
    ny_tz = pytz.timezone("America/New_York")

    msgs = (
        Chat.query.filter(
            ((Chat.sender_id == current_user.id) & (Chat.receiver_id == user_id))
            | ((Chat.sender_id == user_id) & (Chat.receiver_id == current_user.id))
        )
        .order_by(Chat.timestamp)
        .all()
    )

    return jsonify(
        [
            {
                "sender": m.sender_id,
                "content": m.content,
                "time": m.timestamp.replace(tzinfo=pytz.utc)
                .astimezone(ny_tz)
                .strftime("%b %d • %I:%M %p"),
            }
            for m in msgs
        ]
    )


@main.route("/inbox")
@login_required
def inbox():
    users = (
        User.query.join(
            Chat, or_(Chat.sender_id == User.id, Chat.receiver_id == User.id)
        )
        .filter(
            or_(Chat.sender_id == current_user.id, Chat.receiver_id == current_user.id)
        )
        .filter(User.id != current_user.id)
        .distinct()
        .all()
    )

    return render_template("inbox.html", conversations=users)


@main.route("/profile")
@login_required
def profile():
    # Safe check for favorites
    try:
        favorites = (
            current_user.favorites.filter_by(is_deleted=False).all()
            if hasattr(current_user.favorites, "all")
            else [item for item in current_user.favorites if not item.is_deleted]
        )
    except:
        favorites = []

    # Orders placed by this user
    orders = (
        Order.query.filter_by(buyer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(5)  # show only the most recent 5
        .all()
    )

    # Listings posted by this user
    listings = Item.query.filter_by(seller_id=current_user.id, is_deleted=False).all()

    # Convert item IDs -> real Item objects
    # Recently Viewed Items (from relation)
    recent_items = []
    if current_user.is_authenticated:
        views = current_user.viewed_history.order_by(
            RecentlyViewed.viewed_at.desc()
        ).all()
        recent_items = [v.item for v in views if not v.item.is_deleted][:5]

    return render_template(
        "profile.html",
        user=current_user,
        favorites=favorites,
        orders=orders,
        listings=listings,
        recent_items=recent_items,
    )


@main.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    uploaded_image_filename = request.form.get("uploaded_image_filename")
    current_user.first_name = first_name
    current_user.last_name = last_name
    if uploaded_image_filename and uploaded_image_filename != "":
        old_profile_image = current_user.profile_image
        if old_profile_image:
            current_app.s3_client.delete_object(
                Bucket=current_app.s3_bucket_id, Key=old_profile_image
            )
        current_user.profile_image = uploaded_image_filename
    db.session.commit()
    return redirect(url_for("main.profile"))


@main.route("/approve_pickup/<int:order_id>", methods=["POST"])
@login_required
def approve_pickup(order_id):
    order = Order.query.get_or_404(order_id)

    # Security → only the seller of the item can approve
    if order.item.seller_id != current_user.id:
        flash("You are not allowed to approve this order.", "danger")
        return redirect(url_for("main.my_listings"))

    if order.status != "pending":
        flash("This order cannot be approved.", "warning")
        return redirect(url_for("main.my_listings"))

    # Change state to approved
    order.status = "approved"
    order.item.is_active = False
    db.session.commit()

    flash("Pickup approved! The buyer can now pick up the item.", "success")
    return redirect(url_for("main.my_listings"))


@main.route("/mark_sold/<int:order_id>", methods=["POST"])
@login_required
def mark_sold(order_id):
    order = Order.query.get_or_404(order_id)

    # Only seller can mark as sold
    if order.item.seller_id != current_user.id:
        abort(403)

    # Only approved orders can be marked as sold
    if order.status != "approved":
        return jsonify({"success": False, "message": "Order cannot be marked as sold."})

    order.status = "completed"
    db.session.commit()

    return jsonify({"success": True})
