"""Route modules for the application"""

from . import main_routes
from . import admin_routes
from . import order_routes
from . import websocket_handlers

__all__ = ['main_routes', 'admin_routes', 'order_routes', 'websocket_handlers']
