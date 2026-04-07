"""Main application module - refactored and improved"""

import os
import sys
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_caching import Cache

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.database import DataStorage
from src.printer import CupsPrinterManager, PrintQueueManager
from src.orders import OrderManager, OrderFormatter
from src.utils import setup_logging

# Setup logging
logger = setup_logging(
    Config.LOG_FILE,
    Config.LOG_LEVEL,
    Config.LOG_FORMAT,
    Config.LOG_MAX_BYTES,
    Config.LOG_BACKUP_COUNT
)

# Ensure directories exist
Config.ensure_directories()

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.join(Config.BASE_DIR, 'templates'),
            static_folder=os.path.join(Config.BASE_DIR, 'static'))
app.config.from_object(Config)

# Initialize cache
cache = Cache(app)

# Initialize SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6
)

# Initialize data storage
storage = DataStorage(
    Config.DATA_DIR,
    Config.BACKUP_DIR,
    Config.MAX_BACKUPS
)

# Initialize order manager
order_manager = OrderManager(
    storage,
    Config.PRODUCTS_FILE,
    Config.CATEGORIES_FILE,
    Config.ORDERS_FILE
)

# Initialize CUPS printer manager (replaces direct USB connection)
printer_manager = CupsPrinterManager(
    server=Config.CUPS_SERVER,
    port=Config.CUPS_PORT,
    printer_name=Config.CUPS_PRINTER_NAME,
)

# Initialize print queue manager
print_queue_manager = PrintQueueManager(
    printer_manager,
    Config.PRINTER_RETRY_COUNT,
    Config.PRINTER_RETRY_DELAY
)

# Initialize order formatter
order_formatter = OrderFormatter(Config.PRINTER_PAPER_WIDTH)


def start_print_worker():
    """Startet den Drucker-Worker.

    Gibt *True* zurück wenn der Worker gestartet wurde.
    Die Anwendung läuft auch ohne Drucker weiter – Bestellungen können
    dann über die Browser-Druckfunktion (Android-Druckdienst) gedruckt
    werden.
    """
    try:
        if print_queue_manager.start_worker():
            logger.info(
                "CUPS-Drucker-Worker erfolgreich gestartet "
                "(Server: %s:%d)", Config.CUPS_SERVER, Config.CUPS_PORT
            )
            return True
        else:
            logger.warning(
                "CUPS-Drucker-Worker konnte nicht gestartet werden – "
                "Browser-Druck (Android-Druckdienst) steht weiterhin zur Verfügung"
            )
            return False
    except Exception as e:
        logger.warning(
            "Fehler beim Starten des CUPS-Drucker-Workers: %s – "
            "Browser-Druck steht weiterhin zur Verfügung", e
        )
        return False


# Import routes after app initialization
from src.routes import (
    main_routes,
    admin_routes,
    order_routes,
    websocket_handlers
)

# Register routes
main_routes.register_routes(app, order_manager)
admin_routes.register_routes(app, order_manager, storage)
order_routes.register_routes(app, order_manager, order_formatter, print_queue_manager)
websocket_handlers.register_handlers(socketio, order_manager)


@app.template_global()
def now():
    """Template global for current time"""
    from datetime import datetime
    return datetime.now()


@app.template_filter('strftime')
def strftime_filter(date, format):
    """Template filter for date formatting"""
    from datetime import datetime
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date)
        except ValueError:
            return date
    if isinstance(date, datetime):
        return date.strftime(format)
    return str(date)


def create_app():
    """Application factory"""
    return app


if __name__ == '__main__':
    # Start printer worker (non-fatal if CUPS unavailable)
    start_print_worker()

    # Run app
    logger.info("Starte PartyBestellsystem Server")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )
