#!/usr/bin/env python3
"""
Main entry point for PartyBestellsystem
Provides backwards compatibility and easy startup
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the application
from src.app import app, socketio, start_print_worker, logger

if __name__ == '__main__':
    # Printing is now handled client-side via static/receipt.html (browser / Android print service).
    # The USB printer worker is optional – start it if available but don't exit when it's not.
    if not start_print_worker():
        logger.warning("Drucker-Worker nicht gestartet – Browser-Druck steht weiterhin zur Verfügung")

    # Run app
    logger.info("Starte PartyBestellsystem Server")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )
