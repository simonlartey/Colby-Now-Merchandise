"""
API package for Colby Now Merchandise
REST API v1.0
"""

from flask import Blueprint

def create_api_blueprint():
    """Create and configure the API blueprint."""
    api = Blueprint('api', __name__, url_prefix='/api/v1')
    
    # Import route modules
    from . import auth_routes
    from . import items_routes
    from . import orders_routes
    from . import users_routes
    from . import chat_routes
    
    # Register route modules (they will use the api blueprint)
    auth_routes.register_routes(api)
    items_routes.register_routes(api)
    orders_routes.register_routes(api)
    users_routes.register_routes(api)
    chat_routes.register_routes(api)
    
    return api
