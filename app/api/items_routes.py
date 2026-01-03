"""
Items API endpoints
REST endpoints for browsing, creating, updating, and managing items
"""

from app.services.storage_service import delete_file
from app.services.storage_service import validate_item_image_upload
from app.services.storage_service import generate_put_url
from app.services.storage_service import ITEM_IMAGES_FOLDER
from app.services.storage_service import generate_unique_filename
from app.services.storage_service import is_mimetype_allowed
from flask import request, current_app, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from app.models import Item, db, RecentlyViewed
from app.utils.search_utils import generate_embedding
from .responses import (
    success_response,
    error_response,
    validate_json,
    require_api_auth,
    serialize_item,
)


def register_routes(api):
    """Register items routes to the API blueprint."""

    @api.route("/items", methods=["GET"])
    def list_items():
        """
        List all active items with filtering and sorting.

        GET /api/v1/items?search=&category=&seller_type=&condition=&sort_by=newest&page=1&per_page=20

        Query parameters:
        - search: Search term for title/description
        - category: Filter by category
        - seller_type: Filter by seller type
        - condition: Filter by condition
        - sort_by: newest, oldest, price_low, price_high (default: newest)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)

        Responses:
        - 200: List of items with pagination
        """
        # Get query parameters
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        seller_type = request.args.get("seller_type", "").strip()
        condition = request.args.get("condition", "").strip()
        sort_by = request.args.get("sort_by", "newest")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        # Validate pagination
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        # Build query
        query = Item.query.filter_by(is_active=True)

        # Apply search filter
        if search:
            semantic_results = Item.semantic_search(search, limit=100)
            if semantic_results:
                relevant_ids = [item.id for item in semantic_results]
                query = query.filter(Item.id.in_(relevant_ids))
            else:
                query = query.filter(db.false())

        # Apply category filter
        if category:
            query = query.filter_by(category=category)

        # Apply seller type filter
        if seller_type:
            query = query.filter_by(seller_type=seller_type)

        # Apply condition filter
        if condition:
            query = query.filter_by(condition=condition)

        # Apply sorting
        if sort_by == "oldest":
            query = query.order_by(Item.created_at.asc())
        elif sort_by == "price_low":
            query = query.order_by(Item.price.asc())
        elif sort_by == "price_high":
            query = query.order_by(Item.price.desc())
        else:  # newest (default)
            query = query.order_by(Item.created_at.desc())

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        # Serialize items
        items_data = [serialize_item(item) for item in items]

        return success_response(
            data={
                "items": items_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
                "filters": {
                    "search": search,
                    "category": category,
                    "seller_type": seller_type,
                    "condition": condition,
                    "sort_by": sort_by,
                },
            },
            message="Items retrieved successfully",
        )

    @api.route("/items/<int:item_id>", methods=["GET"])
    def get_item(item_id):
        """
        Get a specific item by ID.

        GET /api/v1/items/<item_id>

        Responses:
        - 200: Item details
        - 404: Item not found
        """
        item = Item.query.get(item_id)

        if not item or not item.is_active:
            return error_response(message="Item not found", status_code=404)

        # Track recently viewed (if authenticated)
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

        return success_response(
            data=serialize_item(item), message="Item retrieved successfully"
        )

    @api.route("/items", methods=["POST"])
    @require_api_auth
    @validate_json("title", "price")
    def create_item():
        """
        Create a new item listing.

        POST /api/v1/items

        Request body (JSON):
        {
            "title": "Vintage Jacket",
            "description": "Beautiful vintage jacket...",
            "category": "clothing",
            "size": "M",
            "seller_type": "individual",
            "condition": "good",
            "price": 25.99
        }

        Responses:
        - 201: Item created successfully
        - 400: Validation error
        - 401: Not authenticated
        """
        data = request.get_json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        category = data.get("category", "").strip()
        size = data.get("size", "").strip()
        seller_type = data.get("seller_type", "").strip()
        condition = data.get("condition", "").strip()
        price_str = data.get("price", "")
        uploaded_image_filename = data.get("uploaded_image_filename", "").strip()

        # Validation
        errors = {}

        if not title:
            errors["title"] = "Item title is required"
        elif len(title) > 150:
            errors["title"] = "Title must be 150 characters or less"

        if price_str:
            try:
                price_clean = price_str.replace("$", "").replace(",", "").strip()
                price = float(price_clean)
                if price < 0:
                    raise ValueError()
            except (ValueError, AttributeError):
                errors["price"] = "Price must be a valid positive number"
        else:
            errors["price"] = "Price is required"

        if errors:
            return error_response(
                message="Validation failed", status_code=400, errors=errors
            )

        # Handle image upload
        item_image = None
        if uploaded_image_filename:
            try:
                is_valid, error_message = validate_item_image_upload(
                    item_image=uploaded_image_filename
                )

                if not is_valid:
                    current_app.logger.error(error_message)
                    return error_response(message=error_message, status_code=400)

                item_image = uploaded_image_filename

            except Exception:
                current_app.logger.exception(
                    "There was an error validating the item image."
                )
                return error_response(
                    message="There was an error creating the item. Please try again later.",
                    status_code=500,
                )

        # Create item
        new_item = Item(
            title=title,
            description=description if description else None,
            category=category if category else None,
            size=size if size else None,
            seller_type=seller_type if seller_type else None,
            condition=condition if condition else None,
            price=price,
            item_image=item_image,
            seller_id=current_user.id,
            embedding=generate_embedding(f"{title} {description}"),
        )

        db.session.add(new_item)
        db.session.commit()

        return success_response(
            data=serialize_item(new_item),
            message="Item created successfully",
            status_code=201,
        )

    @api.route("/items/<int:item_id>", methods=["PUT"])
    @require_api_auth
    @validate_json()
    def update_item(item_id):
        """
        Update an existing item.

        PUT /api/v1/items/<item_id>

        Request body: Same as POST /items (all fields optional)

        Responses:
        - 200: Item updated successfully
        - 400: Validation error
        - 403: Not authorized (not item owner)
        - 404: Item not found
        """
        item = Item.query.get(item_id)

        if not item:
            return error_response(message="Item not found", status_code=404)

        # Check authorization
        if item.seller_id != current_user.id:
            return error_response(
                message="Not authorized to update this item", status_code=403
            )

        # Get update data
        data = request.get_json()

        # Update fields
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return error_response(
                    message="Title cannot be empty",
                    status_code=400,
                    errors={"title": "Title is required"},
                )
            elif len(title) > 150:
                return error_response(
                    message="Title must be 150 characters or less",
                    status_code=400,
                    errors={"title": "Title must be 150 characters or less"},
                )
            item.title = title

        if "description" in data:
            item.description = data["description"].strip() or None

        if "category" in data:
            item.category = data["category"].strip() or None

        if "size" in data:
            item.size = data["size"].strip() or None

        if "seller_type" in data:
            item.seller_type = data["seller_type"].strip() or None

        if "condition" in data:
            item.condition = data["condition"].strip() or None

        if "price" in data:
            try:
                price_str = str(data["price"]).replace("$", "").replace(",", "").strip()
                item.price = float(price_str)
                if item.price < 0:
                    raise ValueError()
            except (ValueError, AttributeError):
                return error_response(
                    message="Invalid price",
                    status_code=400,
                    errors={"price": "Price must be a valid positive number"},
                )

        if "is_active" in data:
            item.is_active = bool(data["is_active"])

        # Update image if provided
        uploaded_image_filename = data.get("uploaded_image_filename", "").strip()
        old_item_image = None
        if uploaded_image_filename and uploaded_image_filename != item.item_image:
            try:
                is_valid, error_message = validate_item_image_upload(
                    item_image=uploaded_image_filename
                )
                if not is_valid:
                    current_app.logger.error(error_message)
                    return error_response(
                        message=error_message,
                        status_code=400,
                    )
                old_item_image = item.item_image
                item.item_image = uploaded_image_filename
            except Exception:
                current_app.logger.exception(
                    "There was an error updating the item image."
                )
                return error_response(
                    message="There was an error updating the item. Please try again later.",
                    status_code=500,
                )

        # Update embedding
        item.embedding = generate_embedding(f"{item.title} {item.description or ''}")

        db.session.commit()

        if old_item_image and not delete_file(filename=old_item_image):
            current_app.logger.warning(
                f"Failed to delete old item image: `{old_item_image}`"
            )

        return success_response(
            data=serialize_item(item), message="Item updated successfully"
        )

    @api.route("/items/<int:item_id>", methods=["DELETE"])
    @require_api_auth
    def delete_item(item_id):
        """
        Delete an item listing (soft delete via is_active).

        DELETE /api/v1/items/<item_id>

        Responses:
        - 200: Item deleted
        - 403: Not authorized
        - 404: Item not found
        """
        item = Item.query.get(item_id)

        if not item:
            return error_response(message="Item not found", status_code=404)

        if item.seller_id != current_user.id:
            return error_response(
                message="Not authorized to delete this item", status_code=403
            )

        try:
            item.is_deleted = True
            item.is_active = False
            db.session.commit()
        except Exception:
            current_app.logger.exception("Error deleting item")
            return error_response(
                message="Error deleting item. Please try again later", status_code=500
            )

        return success_response(message="Item deleted successfully", status_code=200)

    @api.route("/items/<int:item_id>/favorites", methods=["POST"])
    @require_api_auth
    def add_favorite(item_id):
        """
        Add item to user's favorites.

        POST /api/v1/items/<item_id>/favorites

        Responses:
        - 200: Added to favorites
        - 404: Item not found
        """
        item = Item.query.get(item_id)

        if not item or not item.is_active:
            return error_response(message="Item not found", status_code=404)

        if not current_user.favorites.filter_by(id=item.id).first():
            current_user.favorites.append(item)
            db.session.commit()

        return success_response(message="Added to favorites")

    @api.route("/items/<int:item_id>/favorites", methods=["DELETE"])
    @require_api_auth
    def remove_favorite(item_id):
        """
        Remove item from user's favorites.

        DELETE /api/v1/items/<item_id>/favorites

        Responses:
        - 200: Removed from favorites
        - 404: Item not found
        """
        item = Item.query.get(item_id)

        if not item:
            return error_response(message="Item not found", status_code=404)

        if current_user.favorites.filter_by(id=item.id).first():
            current_user.favorites.remove(item)
            db.session.commit()

        return success_response(message="Removed from favorites")

    @api.route("/items/autocomplete", methods=["GET"])
    def autocomplete():
        """
        Get search suggestions for autocomplete.

        GET /api/v1/items/autocomplete?q=jacket&limit=8

        Query parameters:
        - q: Search query (required)
        - limit: Max results (default: 8)

        Responses:
        - 200: List of matching items
        """
        query = request.args.get("q", "").strip()
        limit = request.args.get("limit", 8, type=int)

        if limit < 1 or limit > 50:
            limit = 8

        if not query:
            return success_response(data=[], message="No query provided")

        items = (
            Item.query.filter_by(is_active=True)
            .filter(Item.title.ilike(f"%{query}%"))
            .order_by(Item.created_at.desc())
            .limit(limit)
            .all()
        )

        results = [
            {"id": item.id, "title": item.title, "image": item.image_url}
            for item in items
        ]

        return success_response(data=results, message="Autocomplete results retrieved")

    @api.route("/items/item-image-url", methods=["POST"])
    @require_api_auth
    @validate_json("filename", "contentType")
    def item_image_put_url():
        """
        Generates a presigned PUT URL for uploading item images to the app's default storage bucket.

        POST /api/v1/items/item-image-url

        Request body (JSON):
        {
            "filename": "Winter Jacket.png",
            "contentType": "image/png"
        }

        Responses:
        - 200: Item image PUT URL and new filename
        - 400: Missing or invalid request arguments
        - 500: Error generating item image PUT URL.
        """
        data = request.get_json()
        filename = data.get("filename", "").strip()
        content_type = data.get("contentType", "").strip()

        if not filename or not content_type:
            return error_response(
                message="filename and contentType are required.", status_code=400
            )
        if not is_mimetype_allowed(content_type):
            return error_response(
                message=f"Unsupported contentType:`{content_type}`", status_code=400
            )

        new_filename = generate_unique_filename(
            original_filename=filename,
            folder=ITEM_IMAGES_FOLDER,
            content_type=content_type,
        )

        put_url = generate_put_url(filename=new_filename, content_type=content_type)

        if not put_url:
            return error_response(
                message="There was an error generating the item image upload URL. Please try again later.",
                status_code=500,
            )

        return success_response(
            message="Item image upload URL generated successfully",
            status_code=200,
            data={"putUrl": put_url, "newFilename": new_filename},
        )
