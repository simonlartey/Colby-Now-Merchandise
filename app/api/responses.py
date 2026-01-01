"""
REST API Response utilities and decorators
Standardized response format for all API endpoints
"""

from flask import jsonify, request
from functools import wraps
from flask_login import current_user
from app.services.user_service import get_user_activity_stats

# Standard Responses


def success_response(data=None, message="Success", status_code=200):
    """
    Create a standardized success response.
    """
    response = {
        "status": "success",
        "message": message,
        "data": data,
    }
    return jsonify(response), status_code


def error_response(message="An error occurred", status_code=400, errors=None):
    """
    Create a standardized error response.
    """
    response = {
        "status": "error",
        "message": message,
    }

    if errors:
        response["errors"] = errors

    return jsonify(response), status_code


# Authentication Decorators


def require_api_auth(f):
    """
    Require an authenticated user for API access.
    Uses Flask-Login session authentication.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return error_response(
                message="Unauthorized. Please log in.",
                status_code=401,
            )
        return f(*args, **kwargs)

    return decorated_function


def validate_json(*required_fields):
    """
    Validate that a request contains JSON and required fields.

    Usage:
        @validate_json('email', 'password')
        def login():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return error_response(
                    message="Content-Type must be application/json",
                    status_code=400,
                )

            data = request.get_json()
            if not data:
                return error_response(
                    message="Request body cannot be empty",
                    status_code=400,
                )

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return error_response(
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=400,
                    errors={
                        field: "This field is required" for field in missing_fields
                    },
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Serialization Helpers


def serialize_user(user, include_email=False, include_stats=False):
    """
    Serialize a User model into a safe public representation.
    """
    data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "name": user.full_name,
        "profile_image": user.profile_image,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "is_verified": user.is_verified,
    }

    if include_email:
        data["email"] = user.email
    
    if include_stats:
        user_stats = get_user_activity_stats(user)
        for stat in user_stats:
            data[stat] = user_stats[stat]
    return data


def serialize_item(item):
    """
    Serialize an Item model for API responses.
    """
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "size": item.size,
        "seller_type": item.seller_type,
        "condition": item.condition,
        "price": float(item.price),
        "image_url": item.image_url,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "seller_id": item.seller_id,
        "seller": (
            {
                "id": item.seller.id,
                "name": item.seller.full_name,
            }
            if item.seller
            else None
        ),
        "is_active": item.is_active,
    }


def serialize_order(order):
    """
    Serialize an Order model.
    """
    return {
        "id": order.id,
        "buyer_id": order.buyer_id,
        "item_id": order.item_id,
        "status": order.status,
        "location": order.location,
        "notes": order.notes,
        "pickup_time": order.pickup_time.isoformat() if order.pickup_time else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "item": serialize_item(order.item) if order.item else None,
        "buyer": serialize_user(order.buyer) if order.buyer else None,
    }


def serialize_chat_message(chat):
    """
    Serialize a Chat message.
    """
    return {
        "id": chat.id,
        "sender_id": chat.sender_id,
        "receiver_id": chat.receiver_id,
        "content": chat.content,
        "is_read": chat.is_read,
        "timestamp": chat.timestamp.isoformat() if chat.timestamp else None,
        "sender": serialize_user(chat.sender) if chat.sender else None,
    }
