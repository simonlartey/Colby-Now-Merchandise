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
from werkzeug.utils import secure_filename
from .models import Item, Order, User, RecentlyViewed, db
from .search_utils import generate_embedding
import os
from datetime import datetime
from flask_mail import Message
import stripe

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
        Item.query.filter_by(category=category, is_active=True)
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

    # We'll use a base query first
    query = Item.query.filter_by(is_active=True)

    # If search provided, we might need semantic search
    # BUT semantic_search returns a list, not a query object.
    # To combine with other filters (category, etc), we might need a hybrid approach
    # OR helper method. For now, let's keep it simple:
    # If search is present, we get IDs from semantic search and filter by them.

    if search:
        semantic_results = Item.semantic_search(search, limit=50)  # Get top 50 relevant
        if not semantic_results:
            # If no semantic results, maybe fall back to empty or keep broad?
            # Let's result in empty
            query = query.filter(db.false())
        else:
            relevant_ids = [item.id for item in semantic_results]
            query = query.filter(Item.id.in_(relevant_ids))

            # Preserve semantic order if possible?
            # SQL "IN" doesn't preserve order.
            # We will sort by created_at etc below anyway unless specific sort requested.

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

            image_url = None
            if "image" in request.files:
                file = request.files["image"]
                if file and file.filename:
                    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
                    filename = secure_filename(file.filename)
                    if (
                        "." in filename
                        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
                    ):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{filename}"
                        upload_folder = os.path.join(
                            current_app.static_folder, "uploads"
                        )
                        os.makedirs(upload_folder, exist_ok=True)
                        filepath = os.path.join(upload_folder, filename)
                        file.save(filepath)
                        image_url = f"uploads/{filename}"
                    else:
                        flash(
                            "Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, WEBP).",
                            "danger",
                        )
                        return redirect(url_for("main.post_item"))

            if not title:
                flash("Item name is required.", "danger")
                return redirect(url_for("main.post_item"))

            if not price_str:
                flash("Price is required.", "danger")
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
                image_url=image_url,
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
    item = Item.query.get_or_404(item_id)

    # --- Recently Viewed (Upsert Logic) ---
    if current_user.is_authenticated:
        existing_view = RecentlyViewed.query.filter_by(
            user_id=current_user.id, item_id=item.id
        ).first()

        if existing_view:
            existing_view.viewed_at = datetime.utcnow()
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
    query = Item.query.filter_by(seller_id=current_user.id)

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

    paid_orders = [o for o in incoming_orders if o.status == "paid_pending_pickup"]
    pending_orders = [o for o in incoming_orders if o.status == "pending"]
    approved_orders = [o for o in incoming_orders if o.status == "approved"]
    completed_orders = [o for o in incoming_orders if o.status == "delivered"]

    return render_template(
        "my_listings.html",
        items=items,
        paid_orders=paid_orders,
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        completed_orders=completed_orders,
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
    item = Item.query.get_or_404(item_id)

    if item.seller_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("main.my_listings"))

    if request.method == "POST":
        try:
            item.title = request.form.get("title", item.title).strip()
            item.description = request.form.get("description", item.description).strip()
            item.category = request.form.get("category", item.category).strip()
            item.size = request.form.get("size", item.size).strip()
            item.seller_type = request.form.get("seller_type", item.seller_type).strip()
            item.condition = request.form.get("condition", item.condition).strip()

            price_str = request.form.get("price", str(item.price))
            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                item.price = float(price_clean)
            except ValueError:
                flash("Invalid price. Please enter a valid number.", "danger")
                return redirect(url_for("main.edit_item", item_id=item.id))

            # Update embedding
            item.embedding = generate_embedding(f"{item.title} {item.description}")

            if "image" in request.files:
                file = request.files["image"]
                if file and file.filename:
                    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
                    filename = secure_filename(file.filename)
                    if (
                        "." in filename
                        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
                    ):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{filename}"
                        upload_folder = os.path.join(
                            current_app.static_folder, "uploads"
                        )
                        os.makedirs(upload_folder, exist_ok=True)
                        filepath = os.path.join(upload_folder, filename)
                        file.save(filepath)
                        item.image_url = f"uploads/{filename}"

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
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted successfully.", "success")
    return redirect(url_for("main.my_listings"))


@main.route("/order/<int:item_id>", methods=["GET"])
@login_required
def place_order(item_id):
    item = Item.query.get_or_404(item_id)
    if item is None:
        print("cannot find this item")
    return render_template("order_page.html", item=item)


@main.route("/order/<int:item_id>", methods=["POST"])
@login_required
def create_order(item_id):

    # Get form fields
    location = request.form.get("location")
    notes = request.form.get("notes")

    # pickup date + time
    pickup_date = request.form.get("pickup_date")  # ex: 2025-12-08
    pickup_time = request.form.get("pickup_time")  # ex: 14:30

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
        payment_method="stripe",
        pickup_time=combined_pickup_time,
        status="awaiting_payment",
    )

    db.session.add(order)
    db.session.commit()

    # Redirect user to the payment page
    return redirect(url_for("main.payment_page", order_id=order.id))


@main.route("/payment/<int:order_id>")
@login_required
def payment_page(order_id):
    order = Order.query.get_or_404(order_id)

    if order.buyer_id != current_user.id:
        abort(403)

    item = order.item

    return render_template("payment.html", order=order, item=item)


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
    paid_pending_pickup_orders = [
        o for o in orders if o.status == "paid_pending_pickup"
    ]
    approved_orders = [o for o in orders if o.status == "approved"]
    delivered_orders = [o for o in orders if o.status == "delivered"]

    return render_template(
        "my_orders.html",
        paid_pending_pickup_orders=paid_pending_pickup_orders,
        approved_orders=approved_orders,
        delivered_orders=delivered_orders,
        current_search=search,
    )


@main.route("/confirm_order/<int:order_id>", methods=["POST"])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    order.status = "delivered"
    db.session.commit()
    return jsonify({"success": True})


@main.route("/favorites")
@login_required
def favorites():
    fav_items = (
        current_user.favorites.all()
        if hasattr(current_user.favorites, "all")
        else list(current_user.favorites)
    )
    return render_template("favorites.html", favorites=fav_items)


@main.route("/favorites/add/<int:item_id>", methods=["POST"])
@login_required
def add_favorite(item_id):
    item = Item.query.get_or_404(item_id)
    if not current_user.favorites.filter_by(id=item.id).first():
        current_user.favorites.append(item)
        db.session.commit()
        flash("Added to favorites", "success")
    return redirect(request.referrer or url_for("main.favorites"))


@main.route("/favorites/remove/<int:item_id>")
@login_required
def remove_favorite(item_id):
    item = Item.query.get_or_404(item_id)
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
        Item.query.filter(Item.title.ilike(f"%{query}%"))
        .order_by(Item.created_at.desc())
        .limit(8)
        .all()
    )

    results = []
    for item in items:
        image_url = (
            url_for("static", filename=item.image_url)
            if item.image_url
            else url_for("static", filename="images/default_item.png")
        )

        results.append({"id": item.id, "title": item.title, "image": image_url})

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


@main.route("/profile")
@login_required
def profile():
    # Safe check for favorites
    try:
        favorites = (
            current_user.favorites.all()
            if hasattr(current_user.favorites, "all")
            else list(current_user.favorites)
        )
    except:
        favorites = []  # fallback until  favorites page is ready

    # Orders placed by this user
    orders = (
        Order.query.filter_by(buyer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(5)  # show only the most recent 5
        .all()
    )

    # Listings posted by this user
    listings = Item.query.filter_by(seller_id=current_user.id).all()

    # Convert item IDs -> real Item objects
    # Recently Viewed Items (from relation)
    recent_items = []
    if current_user.is_authenticated:
        views = (
            current_user.viewed_history.order_by(RecentlyViewed.viewed_at.desc())
            .limit(5)
            .all()
        )
        recent_items = [v.item for v in views]

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

    current_user.first_name = first_name
    current_user.last_name = last_name

    image = request.files.get("profile_image")
    if image and image.filename != "":
        upload_path = os.path.join(current_app.static_folder, "profile_images")
        os.makedirs(upload_path, exist_ok=True)

        filename = f"{current_user.id}.png"
        filepath = os.path.join(upload_path, filename)
        image.save(filepath)

        # Store RELATIVE path
        current_user.profile_image = f"profile_images/{filename}"
        print("DEBUG: Updating profile image to:", current_user.profile_image)

    db.session.commit()
    return redirect(url_for("main.profile"))


@main.route("/start_checkout/<int:order_id>", methods=["POST"])
@login_required
def start_checkout(order_id):
    # Initialize Stripe safely inside the request context
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

    order = Order.query.get_or_404(order_id)

    # Only the buyer can pay
    if order.buyer_id != current_user.id:
        abort(403)

    item = order.item

    # Stripe requires amounts in CENTS
    amount_cents = int(item.price * 100)

    # Create Stripe Checkout Session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": item.title},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "order_id": order.id,
            "item_id": item.id,
            "buyer_id": current_user.id,
        },
        success_url=url_for("main.payment_success", order_id=order.id, _external=True),
        cancel_url=url_for("main.payment_cancelled", order_id=order.id, _external=True),
    )

    # (Optional but recommended)
    order.stripe_session_id = checkout_session.id
    order.status = "processing_payment"
    db.session.commit()

    # Redirect user to Stripe
    return redirect(checkout_session.url)


@main.route("/payment_success/<int:order_id>")
@login_required
def payment_success(order_id):
    order = Order.query.get_or_404(order_id)

    # Ensure only the buyer can view this
    if order.buyer_id != current_user.id:
        abort(403)

    # Prevent double-processing
    if order.status == "paid_pending_pickup":
        return render_template("payment_success.html", order=order, item=order.item)

    # Update order status
    order.status = "paid_pending_pickup"

    # Hide item from Buy Item list
    item = order.item
    item.is_active = False

    db.session.commit()

    # Render the success UI
    return render_template("payment_success.html", order=order, item=item)


@main.route("/payment_cancelled/<int:order_id>")
@login_required
def payment_cancelled(order_id):
    order = Order.query.get_or_404(order_id)

    # Only buyer can view
    if order.buyer_id != current_user.id:
        abort(403)

    flash("Payment was cancelled. No charges were made.", "warning")
    return redirect(url_for("main.my_orders"))


@main.route("/complete_order/<int:order_id>", methods=["POST"])
@login_required
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)

    # Only seller allowed
    if order.item.seller_id != current_user.id:
        flash("You are not allowed to complete this order.", "danger")
        return redirect(url_for("main.my_listings"))

    # Final order status — unified for buyer & seller
    order.status = "delivered"
    order.completed_at = datetime.utcnow()

    # Item should no longer be visible
    order.item.is_active = False

    db.session.commit()

    flash("Order marked as delivered!", "success")
    return redirect(url_for("main.my_listings"))


@main.route("/approve_pickup/<int:order_id>", methods=["POST"])
@login_required
def approve_pickup(order_id):
    order = Order.query.get_or_404(order_id)

    # Security → only the seller of the item can approve
    if order.item.seller_id != current_user.id:
        flash("You are not allowed to approve this order.", "danger")
        return redirect(url_for("main.my_listings"))

    # Only allow approval for paid orders
    if order.status != "paid_pending_pickup":
        flash("This order cannot be approved.", "warning")
        return redirect(url_for("main.my_listings"))

    # Change state to approved
    order.status = "approved"
    db.session.commit()

    flash("Pickup approved! The buyer can now pick up the item.", "success")
    return redirect(url_for("main.my_listings"))
