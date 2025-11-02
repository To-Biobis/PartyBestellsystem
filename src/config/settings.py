"""Configuration settings for the application"""

import os
import re
import logging
from datetime import timedelta
from werkzeug.security import generate_password_hash


class Config:
    """Application configuration"""
    
    # Basis-Konfiguration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    ADMIN_PASSWORD_HASH = generate_password_hash(
        os.environ.get('ADMIN_PASSWORD', 'admin123')
    )
    
    # Verzeichnisse
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
    
    # Datenpfade
    ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
    CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
    PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
    RECEIPT_TEMPLATE_FILE = os.path.join(DATA_DIR, 'receipt_template.json')
    
    # Backup-Einstellungen
    MAX_BACKUPS = 5
    BACKUP_INTERVAL = 3600  # 1 Stunde
    
    # Validierung
    TABLE_NUMBER_PATTERN = re.compile(r'^\d{1,3}$')
    MAX_ORDERS_PER_TABLE = 100
    
    # Performance-Einstellungen
    PRINT_TIMEOUT = 30
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Cache-Einstellungen
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Server-Einstellungen
    WORKERS = 2
    WORKER_CLASS = 'gevent'
    TIMEOUT = 120
    KEEPALIVE = 5
    MAX_REQUESTS = 1000
    MAX_REQUESTS_JITTER = 50
    
    # Drucker-Konfiguration
    PRINTER_VENDOR_ID = 0x04b8  # Epson Vendor ID
    PRINTER_PRODUCT_ID = 0x0e15  # TM-T20II
    PRINTER_INTERFACE = 0
    PRINTER_TIMEOUT = 5000
    PRINTER_PAPER_WIDTH = 32
    PRINTER_RETRY_COUNT = 3
    PRINTER_RETRY_DELAY = 1
    
    # Logging-Konfiguration
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(BASE_DIR, 'app.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Standard-Bon-Template
    DEFAULT_RECEIPT_TEMPLATE = {
        'header': {
            'text': 'Ihr Restaurant\nBestellung\n',
            'align': 'center',
            'font': 'a',
            'width': 2,
            'height': 2
        },
        'footer': {
            'text': '\nVielen Dank für Ihren Besuch!\n',
            'align': 'center',
            'font': 'a',
            'width': 1,
            'height': 1
        },
        'separator': '=' * 32,
        'order_format': {
            'product': '{menge}x {produkt}',
            'price': '   {menge} x {price:.2f}€ = {total:.2f}€',
            'comment': '   Kommentar: {comment}',
            'time': '   Zeit: {time}'
        }
    }
    
    @classmethod
    def ensure_directories(cls):
        """Erstellt notwendige Verzeichnisse"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
