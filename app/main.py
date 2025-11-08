from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import Item, db, User
import os
from datetime import datetime

# Create a new blueprint for main pages
main = Blueprint("main", __name__)


@main.route("/")
@login_required
def home():
    """
    Displays the homepage after a successful login or signup.
    Requires user to be authenticated.
    """
    categories = ["electronics", "clothing", "furniture"]
    category_items = [
        Item.query.filter_by(category=category).order_by(Item.created_at.desc()).first()
        for category in categories
    ]
    category_items = [
        category_item for category_item in category_items if category_item is not None
    ]
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(6).all()
    return render_template(
        "home.html",
        user=current_user,
        category_items=category_items,
        recent_items=recent_items,
    )


@main.route("/buy_item")
@login_required
def buy_item():
    """
    Displays all items available for purchase with filtering and sorting.
    """
    # Get query parameters
    category = request.args.get("category", type=str)
    seller_type = request.args.get("seller_type", type=str)
    condition = request.args.get("condition", type=str)
    search = request.args.get("search", type=str)
    sort_by = request.args.get("sort_by", default="newest", type=str)

    # Start with base query
    query = Item.query

    # Apply filters
    if category:
        query = query.filter_by(category=category)

    if seller_type:
        query = query.filter_by(seller_type=seller_type)

    if condition:
        query = query.filter_by(condition=condition)

    # Apply search
    if search:
        query = query.filter(
            Item.title.ilike(f"%{search}%") | Item.description.ilike(f"%{search}%")
        )

    # Apply sorting
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

    # Get all items
    items = query.all()

    # Get unique values for filter options
    all_categories = db.session.query(Item.category).distinct().all()
    categories = [cat[0] for cat in all_categories if cat[0]]

    all_seller_types = db.session.query(Item.seller_type).distinct().all()
    seller_types = [st[0] for st in all_seller_types if st[0]]

    all_conditions = db.session.query(Item.condition).distinct().all()
    conditions = [cond[0] for cond in all_conditions if cond[0]]

    return render_template(
        "buy_item.html",
        items=items,
        categories=categories,
        seller_types=seller_types,
        conditions=conditions,
        current_category=category,
        current_seller_type=seller_type,
        current_condition=condition,
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
            # Get form data
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            size = request.form.get("size", "").strip()
            seller_type = request.form.get("seller_type", "").strip()
            condition = request.form.get("condition", "").strip()
            price_str = request.form.get("price", "").strip()

            # Handle file upload
            image_url = None
            if "image" in request.files:
                file = request.files["image"]
                if file and file.filename:
                    # Validate file type
                    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
                    filename = secure_filename(file.filename)

                    # Check if file extension is allowed
                    if (
                        "." in filename
                        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
                    ):
                        # Create unique filename to avoid conflicts
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{filename}"

                        # Create uploads directory if it doesn't exist
                        upload_folder = os.path.join(
                            current_app.static_folder, "uploads"
                        )
                        os.makedirs(upload_folder, exist_ok=True)

                        # Save file
                        filepath = os.path.join(upload_folder, filename)
                        file.save(filepath)

                        # Store relative path for database
                        image_url = f"uploads/{filename}"
                    else:
                        flash(
                            "Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, WEBP).",
                            "danger",
                        )
                        return redirect(url_for("main.post_item"))

            # Basic validation
            if not title:
                flash("Item name is required.", "danger")
                return redirect(url_for("main.post_item"))

            if not price_str:
                flash("Price is required.", "danger")
                return redirect(url_for("main.post_item"))

            # Validate and convert price
            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                price = float(price_clean)
                if price < 0:
                    raise ValueError("Price must be positive")
            except ValueError:
                flash("Invalid price. Please enter a valid number.", "danger")
                return redirect(url_for("main.post_item"))

            # Create new item
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
            )

            db.session.add(new_item)
            db.session.commit()

            flash("Item posted successfully!", "success")
            return redirect(url_for("main.buy_item"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error posting item: {str(e)}", "danger")
            return redirect(url_for("main.post_item"))

    # GET request - show the form
    return render_template("post_new_item.html")


@main.route("/item/<int:item_id>")
@login_required
def item_details(item_id):
    """
    Displays detailed information about a specific item.
    """
    item = Item.query.get_or_404(item_id)
    return render_template("item_details.html", item=item)


@main.route("/seller/<int:seller_id>")
@login_required
def seller_details(seller_id):
    """
    Displays detailed information about a specific seller.
    """
    seller = User.query.get_or_404(seller_id)
    return render_template("sellers_details.html", seller=seller)
