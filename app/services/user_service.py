from app.models import Item, Order


def get_user_activity_stats(user):
    """Business logic for calculating user statistics."""
    return {
        "account_created": (user.created_at.isoformat() if user.created_at else None),
        "is_verified": user.is_verified,
        "listings": {
            "active": Item.query.filter_by(seller_id=user.id, is_active=True).count(),
            "total": Item.query.filter_by(seller_id=user.id).count(),
        },
        "orders": {
            "as_buyer": Order.query.filter_by(buyer_id=user.id).count(),
            "as_seller": Order.query.join(Item)
            .filter(Item.seller_id == user.id)
            .count(),
        },
        "favorites": user.favorites.count(),
        "recently_viewed": user.viewed_history.count(),
    }
