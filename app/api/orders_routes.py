"""
Orders API endpoints
REST endpoints for creating, managing, and tracking orders
"""

from flask import request
from flask_login import current_user
from datetime import datetime

from app.models import Order, Item, db
from .responses import (
    success_response,
    error_response,
    validate_json,
    require_api_auth,
    serialize_order,
)

ALLOWED_STATUSES = {"pending", "approved", "rejected", "completed"}


def register_routes(api):
    """Register orders routes to the API blueprint."""

    # List orders

    @api.route("/orders", methods=["GET"])
    @require_api_auth
    def list_orders():
        """List all orders for current user (buyer or seller)."""
        role = request.args.get("role", "buyer").lower()
        status = request.args.get("status", "").strip()
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)

        if status and status not in ALLOWED_STATUSES:
            return error_response(
                "Invalid order status",
                400,
                {"status": f"Allowed values: {', '.join(ALLOWED_STATUSES)}"},
            )

        if role == "seller":
            query = Order.query.join(Item).filter(Item.seller_id == current_user.id)
        else:
            query = Order.query.filter(Order.buyer_id == current_user.id)

        if status:
            query = query.filter(Order.status == status)

        total = query.count()

        orders = (
            query.order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return success_response(
            data={
                "orders": [serialize_order(order) for order in orders],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
                "filters": {"role": role, "status": status},
            },
            message="Orders retrieved successfully",
        )

    # Get single order

    @api.route("/orders/<int:order_id>", methods=["GET"])
    @require_api_auth
    def get_order(order_id):
        """Get a specific order."""
        order = Order.query.get(order_id)

        if not order:
            return error_response("Order not found", 404)

        is_buyer = order.buyer_id == current_user.id
        is_seller = order.item and order.item.seller_id == current_user.id

        if not (is_buyer or is_seller):
            return error_response("Not authorized to view this order", 403)

        return success_response(
            data=serialize_order(order),
            message="Order retrieved successfully",
        )

    # Create order

    @api.route("/orders", methods=["POST"])
    @require_api_auth
    @validate_json("item_id")
    def create_order():
        """Create a new order."""
        data = request.get_json()

        item = Item.query.get(data["item_id"])
        if not item or not item.is_active:
            return error_response("Item not available", 404)

        if item.seller_id == current_user.id:
            return error_response("You cannot order your own item", 400)

        pickup_time = None
        if data.get("pickup_date") and data.get("pickup_time"):
            try:
                pickup_time = datetime.strptime(
                    f"{data['pickup_date']} {data['pickup_time']}",
                    "%Y-%m-%d %H:%M",
                )
            except ValueError:
                return error_response(
                    "Invalid pickup date or time",
                    400,
                    {
                        "pickup_date": "YYYY-MM-DD",
                        "pickup_time": "HH:MM",
                    },
                )

        order = Order(
            buyer_id=current_user.id,
            item_id=item.id,
            location=data.get("location") or None,
            notes=data.get("notes") or None,
            pickup_time=pickup_time,
            status="pending",
        )

        db.session.add(order)
        db.session.commit()

        return success_response(
            data=serialize_order(order),
            message="Order created successfully",
            status_code=201,
        )

    # Seller actions

    @api.route("/orders/<int:order_id>/approve", methods=["POST"])
    @require_api_auth
    def approve_order(order_id):
        """Approve an order."""
        order = Order.query.get(order_id)
        if not order:
            return error_response("Order not found", 404)

        if order.item.seller_id != current_user.id:
            return error_response("Not authorized", 403)

        if order.status != "pending":
            return error_response("Order cannot be approved", 400)

        order.status = "approved"
        order.item.is_active = False
        db.session.commit()

        return success_response(
            data=serialize_order(order),
            message="Order approved successfully",
        )

    @api.route("/orders/<int:order_id>/reject", methods=["POST"])
    @require_api_auth
    def reject_order(order_id):
        """Reject an order."""
        order = Order.query.get(order_id)
        if not order:
            return error_response("Order not found", 404)

        if order.item.seller_id != current_user.id:
            return error_response("Not authorized", 403)

        if order.status != "pending":
            return error_response("Order cannot be rejected", 400)

        order.status = "rejected"
        db.session.commit()

        return success_response(
            data=serialize_order(order),
            message="Order rejected successfully",
        )

    # Completion & cancellation

    @api.route("/orders/<int:order_id>/complete", methods=["POST"])
    @require_api_auth
    def complete_order(order_id):
        """Mark an order as completed."""
        order = Order.query.get(order_id)
        if not order:
            return error_response("Order not found", 404)

        if order.status != "approved":
            return error_response("Order cannot be completed", 400)

        is_buyer = order.buyer_id == current_user.id
        is_seller = order.item.seller_id == current_user.id

        if not (is_buyer or is_seller):
            return error_response("Not authorized", 403)

        order.status = "completed"
        db.session.commit()

        return success_response(
            data=serialize_order(order),
            message="Order completed successfully",
        )

    @api.route("/orders/<int:order_id>", methods=["DELETE"])
    @require_api_auth
    def cancel_order(order_id):
        """Cancel an order (buyer only)."""
        order = Order.query.get(order_id)
        if not order:
            return error_response("Order not found", 404)

        if order.buyer_id != current_user.id:
            return error_response("Not authorized", 403)

        if order.status not in {"pending", "approved"}:
            return error_response("Order cannot be cancelled", 400)

        if order.status == "approved":
            order.item.is_active = True

        db.session.delete(order)
        db.session.commit()

        return success_response(message="Order cancelled successfully")
