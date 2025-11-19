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
    Supports searching for items by keyword.
    """
    search = request.args.get("search", "").strip()

    if search:
        # User performed a search — show filtered results
        results = Item.search(search).order_by(Item.created_at.desc()).limit(12).all()
        return render_template(
            "home.html",
            user=current_user,
            category_items=[],     # Skip category display during search
            recent_items=results,  # Reuse this section to show results
            current_search=search,
        )

    # Default homepage (no search)
    categories = ["electronics", "clothing", "furniture"]
    category_items = [
        Item.query.filter_by(category=category).order_by(Item.created_at.desc()).first()
        for category in categories
    ]
    category_items = [item for item in category_items if item]
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(6).all()

    return render_template(
        "home.html",
        user=current_user,
        category_items=category_items,
        recent_items=recent_items,
        current_search=None,
    )


@main.route("/buy_item")
@login_required
def buy_item():
    """
    Displays all items available for purchase with filtering and sorting.
    """
    category = request.args.get("category", type=str)
    seller_type = request.args.get("seller_type", type=str)
    condition = request.args.get("condition", type=str)
    search = request.args.get("search", type=str)
    sort_by = request.args.get("sort_by", default="newest", type=str)

    query = Item.search(search)

    if category:
        query = query.filter_by(category=category)
    if seller_type:
        query = query.filter_by(seller_type=seller_type)
    if condition:
        query = query.filter_by(condition=condition)

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


@main.route('/my_listings')
@login_required
def my_listings():
    """Display all items posted by the logged-in user."""
    search = request.args.get("search", "")
    query = Item.search(search).filter_by(seller_id=current_user.id)
    items = query.all()

    if not items:
        flash("You haven’t posted any listings yet.", "info")

    return render_template('my_listings.html', items=items, user=current_user, current_search=search)


@main.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)

    if item.seller_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.my_listings'))

    if request.method == 'POST':
        try:
            item.title = request.form.get('title', item.title).strip()
            item.description = request.form.get('description', item.description).strip()
            item.category = request.form.get('category', item.category).strip()
            item.size = request.form.get('size', item.size).strip()
            item.seller_type = request.form.get('seller_type', item.seller_type).strip()
            item.condition = request.form.get('condition', item.condition).strip()

            price_str = request.form.get('price', str(item.price))
            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                item.price = float(price_clean)
            except ValueError:
                flash("Invalid price. Please enter a valid number.", "danger")
                return redirect(url_for('main.edit_item', item_id=item.id))

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
                        upload_folder = os.path.join(current_app.static_folder, "uploads")
                        os.makedirs(upload_folder, exist_ok=True)
                        filepath = os.path.join(upload_folder, filename)
                        file.save(filepath)
                        item.image_url = f"uploads/{filename}"

            db.session.commit()
            flash("Listing updated successfully!", "success")
            return redirect(url_for('main.my_listings'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating item: {str(e)}", "danger")
            return redirect(url_for('main.edit_item', item_id=item.id))

    return render_template('edit_item.html', item=item)


@main.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.seller_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.my_listings'))
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted successfully.", "success")
    return redirect(url_for('main.my_listings'))


@main.route('/contact-us', methods=['GET'])
def contact_us():
    """
    Displays the contact us page.
    """
    return render_template('contact_us.html')