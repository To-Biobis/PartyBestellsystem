import json
import os
from datetime import datetime, timedelta
import threading
import time
import logging
from logging import handlers  # Expliziter Import für handlers
import psutil
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, emit
from functools import wraps
import secrets
from werkzeug.security import check_password_hash, generate_password_hash
import re
import subprocess
from flask_caching import Cache
from escpos.printer import Usb
import shutil
import atexit
import uuid
import glob
from queue import Queue
from threading import Lock
import queue
import sys

# Konfiguration
class Config:
    # Basis-Konfiguration
    SECRET_KEY = 'your-secret-key-here'  # Bitte ändern Sie diesen Schlüssel!
    ADMIN_PASSWORD_HASH = generate_password_hash('admin123')  # Standard-Passwort: admin123
    DATA_DIR = 'data'
    BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
    TEMP_DIR = tempfile.gettempdir()
    ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
    CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
    PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
    RECEIPT_TEMPLATE_FILE = os.path.join(DATA_DIR, 'receipt_template.json')
    
    # Backup-Einstellungen
    MAX_BACKUPS = 5  # Maximale Anzahl der Backups pro Datei
    BACKUP_INTERVAL = 3600  # Backup-Intervall in Sekunden (1 Stunde)
    
    # Validierung
    TABLE_NUMBER_PATTERN = re.compile(r'^\d{1,3}$')  # 1-3 stellige Zahlen
    MAX_ORDERS_PER_TABLE = 100
    
    # Performance-Einstellungen für Raspberry Pi 3
    PRINT_TIMEOUT = 30  # Erhöht auf 30 Sekunden für bessere Stabilität
    SESSION_COOKIE_SECURE = False  # Auf False für lokale Entwicklung
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Cache-Einstellungen
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 Minuten Cache
    
    # Server-Einstellungen für Raspberry Pi 3
    WORKERS = 2  # Angepasst an die CPU-Kerne des Raspberry Pi 3
    WORKER_CLASS = 'gevent'
    TIMEOUT = 120
    KEEPALIVE = 5
    MAX_REQUESTS = 1000
    MAX_REQUESTS_JITTER = 50
    
    # Drucker-Konfiguration für Windows
    PRINTER_VENDOR_ID = 0x04b8  # Epson Vendor ID
    PRINTER_PRODUCT_ID = 0x0e15  # Korrekte Product ID für TM-T20II
    PRINTER_INTERFACE = 0  # Interface-Nummer
    PRINTER_TIMEOUT = 5000  # Erhöhter Timeout für Windows (5 Sekunden)
    PRINTER_PAPER_WIDTH = 32  # Papierbreite in Zeichen (80mm Papier)
    PRINTER_RETRY_COUNT = 3  # Anzahl der Versuche beim Drucken
    PRINTER_RETRY_DELAY = 1  # Verzögerung zwischen Versuchen in Sekunden
    
    # Logging-Konfiguration
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_FILE = 'app.log'
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

# Logging konfigurieren
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
    handlers=[
        handlers.RotatingFileHandler(  # Verwende den explizit importierten handlers
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)
app.config.from_object(Config)

# Cache initialisieren
cache = Cache(app)

# SocketIO mit optimierten Einstellungen für Raspberry Pi 3
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',  # Verwende threading statt gevent für bessere Kompatibilität
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6  # 1 MB
)

# Globale Template-Funktion für aktuelle Zeit
@app.template_global()
def now():
    return datetime.now()

# Template-Filter für strftime
@app.template_filter('strftime')
def strftime_filter(date, format):
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date)
        except ValueError:
            return date
    if isinstance(date, datetime):
        return date.strftime(format)
    return str(date)

# Thread-sichere Datenstrukturen
class ThreadSafeDict:
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

    def delete(self, key):
        with self._lock:
            if key in self._data:
                del self._data[key]

    def items(self):
        with self._lock:
            return list(self._data.items())

# Globale Variablen mit Thread-Sicherheit
print_timers = ThreadSafeDict()
last_orders = ThreadSafeDict()

# Globale Variablen für den Drucker-Worker
print_queue = Queue()
print_lock = Lock()
MAX_RETRIES = 3
RETRY_DELAY = 1  # Sekunden
printer_thread = None  # Globale Variable für den Thread
printer_instance = None  # Globale Variable für die Druckerinstanz
worker_active = False  # Flag für den Worker-Status

class PrinterManager:
    """Singleton-Klasse zur Verwaltung des Druckers"""
    _instance = None
    _lock = Lock()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.printer = None
        self.last_used = 0
        self._lock = Lock()
    
    def get_printer(self):
        """Gibt eine Druckerinstanz zurück oder erstellt eine neue."""
        with self._lock:
            current_time = time.time()
            # Wenn der Drucker älter als 5 Sekunden ist oder nicht existiert, erstelle eine neue Instanz
            if self.printer is None or (current_time - self.last_used) > 5:
                try:
                    if self.printer is not None:
                        try:
                            self.printer.close()
                        except:
                            pass
                    self.printer = find_printer()
                    self.last_used = current_time
                except Exception as e:
                    logger.error(f"Fehler beim Erstellen der Druckerinstanz: {str(e)}")
                    self.printer = None
            return self.printer
    
    def release_printer(self):
        """Gibt die Druckerinstanz frei."""
        with self._lock:
            if self.printer is not None:
                try:
                    self.printer.close()
                except:
                    pass
                self.printer = None

def reset_printer():
    """Setzt den Drucker zurück, falls er blockiert ist."""
    try:
        # Versuche den Drucker über USB zurückzusetzen
        vendor_id = f"{Config.PRINTER_VENDOR_ID:04x}"
        product_id = f"{Config.PRINTER_PRODUCT_ID:04x}"
        
        # Suche nach dem USB-Gerät
        lsusb_cmd = f"lsusb -d {vendor_id}:{product_id}"
        try:
            result = subprocess.run(lsusb_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                # Gerät gefunden, versuche es zurückzusetzen
                bus_device = result.stdout.split()[1:3]  # Format: "Bus XXX Device XXX"
                if len(bus_device) == 2:
                    bus, device = bus_device
                    reset_cmd = f"sudo usb_modeswitch -b {bus} -g {device} -R"
                    subprocess.run(reset_cmd, shell=True, timeout=5)
                    logger.info(f"Drucker zurückgesetzt (Bus {bus}, Device {device})")
                    time.sleep(2)  # Warte nach dem Zurücksetzen
                    return True
        except Exception as e:
            logger.warning(f"Fehler beim Zurücksetzen des Druckers: {str(e)}")
        
        # Alternative: Versuche den Drucker über sysfs zurückzusetzen
        try:
            for usb_path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
                try:
                    with open(usb_path, 'r') as f:
                        if f.read().strip() == vendor_id:
                            device_path = os.path.dirname(usb_path)
                            reset_path = os.path.join(device_path, "authorized")
                            if os.path.exists(reset_path):
                                # Deaktiviere und aktiviere das Gerät
                                with open(reset_path, 'w') as f:
                                    f.write("0")
                                time.sleep(1)
                                with open(reset_path, 'w') as f:
                                    f.write("1")
                                logger.info("Drucker über sysfs zurückgesetzt")
                                time.sleep(2)
                                return True
                except Exception as e:
                    continue
        except Exception as e:
            logger.warning(f"Fehler beim sysfs-Reset: {str(e)}")
            
        return False
    except Exception as e:
        logger.error(f"Fehler beim Zurücksetzen des Druckers: {str(e)}")
        return False

def printer_worker():
    """Hintergrundprozess für Druckaufträge"""
    global worker_active
    logger.info("Drucker-Worker gestartet")
    worker_active = True
    printer_manager = PrinterManager.get_instance()
    
    try:
        while worker_active:
            try:
                # Warte auf neuen Druckauftrag
                logger.debug("Warte auf neuen Druckauftrag...")
                print_job = print_queue.get(timeout=1)  # Timeout nach 1 Sekunde
                if print_job is None:
                    logger.info("Drucker-Worker beendet")
                    break
                    
                content, retry_count, order_ids = print_job
                logger.info(f"Verarbeite Druckauftrag für Bestellungen {order_ids} (Versuch {retry_count + 1})")
                success = False
                
                try:
                    with print_lock:
                        # Hole eine neue Druckerinstanz
                        printer = printer_manager.get_printer()
                        if printer:
                            logger.info(f"Versuche Druckauftrag für Bestellungen {order_ids} auszuführen")
                            try:
                                # Warte kurz vor dem Drucken
                                time.sleep(0.5)
                                
                                # Führe den Druckauftrag aus
                                printer.text(content)
                                printer.cut()
                                success = True
                                logger.info(f"Druckauftrag für Bestellungen {order_ids} erfolgreich ausgeführt")
                                
                                # Warte kurz nach dem Drucken
                                time.sleep(0.5)
                            except Exception as print_error:
                                logger.error(f"Fehler beim Drucken: {str(print_error)}")
                                # Warte länger bei einem Fehler
                                time.sleep(1)
                                raise
                        else:
                            logger.error("Drucker nicht verfügbar beim Ausführen des Auftrags")
                except Exception as e:
                    logger.error(f"Druckfehler für Bestellungen {order_ids}: {str(e)}")
                    if retry_count < MAX_RETRIES:
                        time.sleep(RETRY_DELAY * (retry_count + 1))  # Exponentielles Backoff
                        logger.info(f"Füge Druckauftrag für Bestellungen {order_ids} erneut zur Warteschlange hinzu")
                        print_queue.put((content, retry_count + 1, order_ids))
                    else:
                        logger.error(f"Maximale Anzahl an Wiederholungsversuchen für Bestellungen {order_ids} erreicht")
                        # Setze Status zurück auf "neu" bei endgültigem Fehler
                        for order_id in order_ids:
                            for bestellung in bestellungen:
                                if bestellung['id'] == order_id and bestellung['status'] == 'in_druck':
                                    bestellung['status'] = 'neu'
                        save_data(Config.ORDERS_FILE, bestellungen)
                finally:
                    if success:
                        try:
                            # Markiere Bestellungen als erledigt nur wenn der Druck erfolgreich war
                            for order_id in order_ids:
                                for bestellung in bestellungen:
                                    if bestellung['id'] == order_id and bestellung['status'] == 'in_druck':
                                        bestellung['status'] = 'erledigt'
                                        bestellung['erledigt_um'] = datetime.now().isoformat()
                                        logger.info(f"Bestellung {order_id} als erledigt markiert")
                            # Speichere die aktualisierten Bestellungen
                            save_data(Config.ORDERS_FILE, bestellungen)
                            logger.info(f"Status für Bestellungen {order_ids} aktualisiert")
                        except Exception as e:
                            logger.error(f"Fehler beim Markieren der Bestellungen {order_ids} als erledigt: {str(e)}")
                    print_queue.task_done()
                    logger.debug("Druckauftrag verarbeitet")
            except queue.Empty:
                # Timeout beim Warten auf neue Aufträge - normal
                continue
            except Exception as e:
                logger.error(f"Fehler im Drucker-Worker: {str(e)}")
                time.sleep(1)
    finally:
        worker_active = False
        printer_manager.release_printer()
        logger.info("Drucker-Worker beendet und Ressourcen freigegeben")

def start_printer_worker():
    """Startet den Drucker-Worker Thread und überprüft seinen Status."""
    global printer_thread, worker_active
    try:
        # Prüfe ob der Thread bereits läuft
        if printer_thread is not None and printer_thread.is_alive() and worker_active:
            logger.info("Drucker-Worker läuft bereits")
            return True
            
        # Beende alten Thread falls vorhanden
        if printer_thread is not None and printer_thread.is_alive():
            logger.info("Beende alten Drucker-Worker")
            worker_active = False
            printer_thread.join(timeout=5)
            
        # Versuche den Drucker zurückzusetzen
        if not reset_printer():
            logger.warning("Konnte Drucker nicht zurücksetzen, versuche trotzdem fortzufahren")
            
        # Warte kurz nach dem Reset
        time.sleep(2)
            
        # Teste den Drucker vor dem Start des Workers
        printer_manager = PrinterManager.get_instance()
        printer = printer_manager.get_printer()
        if printer:
            try:
                logger.info("Führe initialen Drucker-Test durch")
                # Versuche den Drucker mehrmals zu initialisieren
                for attempt in range(3):
                    try:
                        printer.text("Drucker-Test beim Start\n")
                        printer.cut()
                        logger.info("Initialer Drucker-Test erfolgreich")
                        break
                    except Exception as test_error:
                        if attempt < 2:  # Nicht beim letzten Versuch
                            logger.warning(f"Drucker-Test fehlgeschlagen (Versuch {attempt + 1}), warte und versuche erneut")
                            time.sleep(2)
                            printer = printer_manager.get_printer()  # Versuche neue Verbindung
                        else:
                            raise test_error
            except Exception as test_error:
                logger.error(f"Fehler beim initialen Drucker-Test: {str(test_error)}")
                printer_manager.release_printer()
                return False
        else:
            logger.error("Drucker nicht verfügbar beim Start des Workers")
            return False
            
        # Starte neuen Thread
        worker_active = True
        printer_thread = threading.Thread(target=printer_worker, daemon=True, name="PrinterWorker")
        printer_thread.start()
        
        # Warte kurz und prüfe ob der Thread gestartet wurde
        time.sleep(0.5)
        if printer_thread.is_alive() and worker_active:
            logger.info("Drucker-Worker Thread erfolgreich gestartet")
            return True
        else:
            logger.error("Drucker-Worker Thread konnte nicht gestartet werden")
            worker_active = False
            return False
    except Exception as e:
        logger.error(f"Fehler beim Starten des Drucker-Workers: {str(e)}")
        worker_active = False
        return False

def print_order(printer, content, order_ids):
    """Fügt einen Druckauftrag zur Warteschlange hinzu"""
    try:
        print_queue.put((content, 0, order_ids))
        app.logger.info(f"Druckauftrag zur Warteschlange hinzugefügt für Bestellungen {order_ids}")
        return True
    except Exception as e:
        app.logger.error(f"Fehler beim Hinzufügen zum Druckauftrag: {str(e)}")
        return False

def create_backup(file_path):
    """Erstellt ein Backup der angegebenen Datei."""
    try:
        if not os.path.exists(file_path):
            return
            
        # Erstelle Backup-Verzeichnis falls nicht vorhanden
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        
        # Generiere Backup-Dateinamen mit Zeitstempel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(Config.BACKUP_DIR, os.path.basename(file_path))
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"{timestamp}.json")
        
        # Kopiere die Datei
        shutil.copy2(file_path, backup_file)
        
        # Lösche alte Backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.json')])
        while len(backups) > Config.MAX_BACKUPS:
            os.remove(os.path.join(backup_dir, backups.pop(0)))
            
        logger.info(f"Backup erstellt: {backup_file}")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Backups für {file_path}: {str(e)}")

def atomic_save(file_path, data):
    """Speichert Daten atomar in eine Datei."""
    try:
        # Erstelle temporäre Datei
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=os.path.dirname(file_path))
        
        # Schreibe Daten in temporäre Datei
        json.dump(data, temp_file, ensure_ascii=False, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        
        # Backup erstellen
        if os.path.exists(file_path):
            create_backup(file_path)
        
        # Verschiebe temporäre Datei an Zielort
        shutil.move(temp_file.name, file_path)
        
        logger.info(f"Daten gespeichert in {file_path}: {len(data)} Einträge")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Daten in {file_path}: {str(e)}")
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        return False

def save_data(file_path, data):
    """Speichert Daten in eine Datei mit Backup."""
    return atomic_save(file_path, data)

def load_data(file_path, default=None):
    """Lädt Daten aus einer Datei mit Fehlerbehandlung."""
    try:
        if not os.path.exists(file_path):
            if default is None:
                default = []
            atomic_save(file_path, default)
            return default
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Daten geladen aus {file_path}: {len(data)} Einträge")
        return data
    except json.JSONDecodeError:
        logger.error(f"Fehler beim Laden der Daten aus {file_path}: Ungültiges JSON-Format")
        # Versuche das letzte Backup zu laden
        backup_dir = os.path.join(Config.BACKUP_DIR, os.path.basename(file_path))
        if os.path.exists(backup_dir):
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.json')], reverse=True)
            if backups:
                backup_file = os.path.join(backup_dir, backups[0])
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"Daten aus Backup geladen: {backup_file}")
                    atomic_save(file_path, data)  # Stelle die Datei wieder her
                    return data
                except Exception as e:
                    logger.error(f"Fehler beim Laden des Backups {backup_file}: {str(e)}")
        return default if default is not None else []
    except Exception as e:
        logger.error(f"Fehler beim Laden der Daten aus {file_path}: {str(e)}")
        return default if default is not None else []

# Registriere Backup-Timer beim Start
def start_backup_timer():
    """Startet den Backup-Timer."""
    def backup_timer():
        while True:
            time.sleep(Config.BACKUP_INTERVAL)
            try:
                create_backup(Config.ORDERS_FILE)
                create_backup(Config.CATEGORIES_FILE)
                create_backup(Config.PRODUCTS_FILE)
                create_backup(Config.RECEIPT_TEMPLATE_FILE)
            except Exception as e:
                logger.error(f"Fehler beim automatischen Backup: {str(e)}")
    
    backup_thread = threading.Thread(target=backup_timer, daemon=True)
    backup_thread.start()

# Starte Backup-Timer beim Programmstart
start_backup_timer()

# Stelle sicher, dass das Datenverzeichnis existiert
os.makedirs(Config.DATA_DIR, exist_ok=True)
os.makedirs(Config.BACKUP_DIR, exist_ok=True)

# Lade initiale Daten
kategorien = load_data(Config.CATEGORIES_FILE, [])
produkte = load_data(Config.PRODUCTS_FILE, [])
bestellungen = load_data(Config.ORDERS_FILE, [])

def validate_table_number(table):
    """Validiert die Tischnummer."""
    return bool(Config.TABLE_NUMBER_PATTERN.match(str(table)))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bitte als Admin einloggen')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def cleanup_timers():
    """Bereinigt abgelaufene Timer."""
    current_time = time.time()
    for tisch, timer in list(print_timers.items()):
        if not timer.is_alive():
            print_timers.delete(tisch)
            last_orders.delete(tisch)

def find_printer():
    """Findet und initialisiert den Drucker mit verbesserter Fehlerbehandlung"""
    try:
        # Erster Versuch mit Standard-Endpunkten
        printer = Usb(idVendor=0x04b8, idProduct=0x0e15, in_ep=0x82, out_ep=0x01, timeout=0)
        app.logger.info("Drucker erfolgreich initialisiert")
        return printer
    except Exception as e1:
        app.logger.warning(f"Erster Initialisierungsversuch fehlgeschlagen: {str(e1)}")
        try:
            # Zweiter Versuch mit alternativen Endpunkten
            printer = Usb(idVendor=0x04b8, idProduct=0x0e15, in_ep=0x81, out_ep=0x03, timeout=0)
            app.logger.info("Drucker mit alternativen Endpunkten initialisiert")
            return printer
        except Exception as e2:
            app.logger.error(f"Beide Initialisierungsversuche fehlgeschlagen: {str(e2)}")
            return None

def check_printer_status():
    """Überprüft den Status des Druckers."""
    try:
        printer = find_printer()
        if printer:
            try:
                # Versuche einen Testdruck
                printer.text("Test\n")
                printer.cut()
                logger.info("Drucker ist verfügbar und funktioniert")
                return True
            except Exception as test_error:
                logger.error(f"Fehler beim Testdruck: {str(test_error)}")
                return False
        logger.error("Drucker nicht gefunden")
        return False
    except Exception as e:
        logger.error(f"Fehler beim Prüfen des Druckerstatus: {str(e)}")
        return False

def load_receipt_template():
    """Lädt das Bon-Template aus der JSON-Datei."""
    try:
        if os.path.exists(Config.RECEIPT_TEMPLATE_FILE):
            with open(Config.RECEIPT_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return Config.DEFAULT_RECEIPT_TEMPLATE.copy()
    except Exception as e:
        logger.error(f"Fehler beim Laden des Bon-Templates: {str(e)}")
        return Config.DEFAULT_RECEIPT_TEMPLATE.copy()

def save_receipt_template(template):
    """Speichert das Bon-Template in der JSON-Datei."""
    try:
        with open(Config.RECEIPT_TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        logger.info("Bon-Template gespeichert")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Bon-Templates: {str(e)}")
        return False

def delete_completed_orders():
    """Löscht nur Bestellungen, die tatsächlich als erledigt markiert sind."""
    try:
        global bestellungen
        # Zähle die Bestellungen vor dem Löschen
        before_count = len(bestellungen)
        # Behalte nur neue, in_druck und archivierte Bestellungen
        bestellungen = [b for b in bestellungen if b['status'] in ['neu', 'in_druck', 'archiviert']]
        # Zähle die gelöschten Bestellungen
        deleted_count = before_count - len(bestellungen)
        if deleted_count > 0:
            save_data(Config.ORDERS_FILE, bestellungen)
            logger.info(f"{deleted_count} erledigte Bestellungen wurden gelöscht")
        else:
            logger.info("Keine erledigten Bestellungen zum Löschen vorhanden")
    except Exception as e:
        logger.error(f"Fehler beim Löschen erledigter Bestellungen: {str(e)}")

def check_and_print_orders(tisch):
    """Druckt Bestellungen für einen Tisch nach Kategorien getrennt."""
    try:
        # Stelle sicher, dass der Drucker-Worker läuft
        if not start_printer_worker():
            logger.error("Drucker-Worker ist nicht aktiv")
            return
            
        logger.info(f"Überprüfe Bestellungen für Tisch {tisch}")
        # Hole nur neue Bestellungen und markiere sie als "in_druck"
        tisch_bestellungen = []
        for bestellung in bestellungen:
            if str(bestellung['tisch']) == str(tisch) and bestellung['status'] == 'neu':
                bestellung['status'] = 'in_druck'  # Temporärer Status
                tisch_bestellungen.append(bestellung)
        
        if tisch_bestellungen:
            logger.info(f"Neue Bestellungen für Tisch {tisch} gefunden: {len(tisch_bestellungen)}")
            
            # Speichere den Status "in_druck"
            save_data(Config.ORDERS_FILE, bestellungen)
            
            # Gruppiere Bestellungen nach Kategorien
            kategorie_bestellungen = {}
            for bestellung in tisch_bestellungen:
                produkt = next((p for p in produkte if p['name'] == bestellung['produkt']), None)
                if produkt:
                    kategorie_id = produkt['kategorie']
                    if kategorie_id not in kategorie_bestellungen:
                        kategorie_bestellungen[kategorie_id] = []
                    kategorie_bestellungen[kategorie_id].append(bestellung)
            
            # Erstelle und drucke für jede Kategorie einen separaten Zettel
            for kategorie_id, bestellungen_kat in kategorie_bestellungen.items():
                # Finde den Kategorienamen
                kategorie = next((k for k in kategorien if k['id'] == kategorie_id), None)
                kategorie_name = kategorie['name'] if kategorie else f"Kategorie {kategorie_id}"
                
                # Sammle die IDs der Bestellungen für diese Kategorie
                order_ids = [b['id'] for b in bestellungen_kat]
                logger.info(f"Erstelle Druckauftrag für Kategorie {kategorie_name} mit Bestellungen {order_ids}")
                
                # Erstelle Text-Inhalt für diese Kategorie
                text_content = []
                text_content.append(f"Tisch {tisch} - {kategorie_name}\n")
                text_content.append("=" * Config.PRINTER_PAPER_WIDTH + "\n")
                
                # Berechne Gesamtpreis für diese Kategorie
                kategorie_gesamtpreis = 0.0
                
                for bestellung in bestellungen_kat:
                    zeitpunkt = datetime.fromisoformat(bestellung['zeitpunkt']).strftime('%H:%M')
                    einzelpreis = bestellung.get('price', 0.0)
                    gesamtpreis = einzelpreis * bestellung['menge']
                    kategorie_gesamtpreis += gesamtpreis
                    
                    text_content.append(f"{bestellung['menge']}x {bestellung['produkt']}\n")
                    text_content.append(f"   {bestellung['menge']} x {einzelpreis:.2f}€ = {gesamtpreis:.2f}€\n")
                    if bestellung.get('kommentar'):
                        text_content.append(f"   Kommentar: {bestellung['kommentar']}\n")
                    text_content.append(f"   Zeit: {zeitpunkt}\n")
                    text_content.append("-" * Config.PRINTER_PAPER_WIDTH + "\n")
                
                # Füge Gesamtpreis für die Kategorie hinzu
                text_content.append(f"\nGesamtpreis {kategorie_name}: {kategorie_gesamtpreis:.2f}€\n")
                text_content.append("=" * Config.PRINTER_PAPER_WIDTH + "\n\n")
                
                # Füge den Druckauftrag zur Warteschlange hinzu
                if not print_order(None, "".join(text_content), order_ids):
                    logger.error(f"Fehler beim Hinzufügen des Druckauftrags für Kategorie {kategorie_name}")
                    # Setze Status zurück auf "neu" bei Fehler
                    for bestellung in bestellungen_kat:
                        bestellung['status'] = 'neu'
                    save_data(Config.ORDERS_FILE, bestellungen)
                    continue
                
                logger.info(f"Druckauftrag für Kategorie {kategorie_name} wurde zur Warteschlange hinzugefügt")
            
        else:
            logger.info(f"Keine neuen Bestellungen für Tisch {tisch}")
            
    except Exception as e:
        logger.error(f"Fehler beim Drucken für Tisch {tisch}: {str(e)}", exc_info=True)
        # Setze Status zurück auf "neu" bei Fehler
        for bestellung in tisch_bestellungen:
            bestellung['status'] = 'neu'
        save_data(Config.ORDERS_FILE, bestellungen)
    finally:
        # Timer neu starten
        timer = threading.Timer(30.0, start_print_timer, args=[tisch])
        timer.start()
        print_timers.set(tisch, timer)

def start_print_timer(tisch):
    """Startet einen Timer für den automatischen Druck."""
    try:
        # Prüfe ob es neue Bestellungen gibt
        tisch_bestellungen = [b for b in bestellungen if str(b['tisch']) == str(tisch) and b['status'] == 'neu']
        if tisch_bestellungen:
            check_and_print_orders(tisch)
        
        # Starte neuen Timer
        timer = threading.Timer(30.0, start_print_timer, args=[tisch])
        timer.start()
        print_timers.set(tisch, timer)
        logger.info(f"Timer für Tisch {tisch} neu gestartet")
    except Exception as e:
        logger.error(f"Fehler beim Starten des Druck-Timers für Tisch {tisch}: {str(e)}")

# Performance-Metriken
class PerformanceMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self._lock = threading.Lock()
        
    def increment_request(self):
        with self._lock:
            self.request_count += 1
            
    def get_metrics(self):
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'uptime': time.time() - self.start_time,
            'request_count': self.request_count,
            'cpu_percent': psutil.cpu_percent(),
            'memory_usage': memory_info.rss / 1024 / 1024,  # MB
            'memory_percent': process.memory_percent(),
            'thread_count': threading.active_count(),
            'disk_usage': psutil.disk_usage('/').percent
        }

# Globale Performance-Metriken
performance_metrics = PerformanceMetrics()

@app.before_request
def before_request():
    """Führt Vorbereitungen vor jeder Anfrage durch."""
    cleanup_timers()
    performance_metrics.increment_request()
    # Stelle sicher, dass die Session permanent ist
    session.permanent = True
    # Setze Session-Cookie-Optionen
    session.modified = True
    logger.debug(f"Session vor Request: {dict(session)}")

@app.after_request
def after_request(response):
    """Logging nach jeder Anfrage."""
    logger.debug(f"Session nach Request: {dict(session)}")
    return response

@app.route('/', methods=['GET'])
def table_selection():
    if 'current_table' in session:
        return redirect(url_for('order_page'))
    return render_template('table_selection.html')

@app.route('/set-table', methods=['POST'])
def set_table():
    table = request.form.get('table', '').strip()
    if not validate_table_number(table):
        flash('Ungültige Tischnummer. Bitte geben Sie eine Zahl zwischen 1 und 999 ein.')
        return redirect(url_for('table_selection'))
    session['current_table'] = table
    return redirect(url_for('order_page'))

@app.route('/new-table')
def new_table():
    session.pop('current_table', None)
    return redirect(url_for('table_selection'))

@app.route('/orders', methods=['GET', 'POST'])
def order_page():
    if request.method == 'GET':
        if 'current_table' not in session:
            logger.warning("Zugriff auf /orders ohne Tischnummer")
            return redirect(url_for('table_selection'))

        # Lade aktuelle Daten
        tisch = str(session['current_table'])
        tisch_bestellungen = [b for b in bestellungen if str(b.get('tisch', '')) == tisch]
        
        # Berechne Gesamtpreis
        gesamtpreis = sum(calculate_order_total(b) for b in tisch_bestellungen)
        
        return render_template('index.html', 
                             kategorien=kategorien, 
                             produkte=produkte, 
                             bestellungen=tisch_bestellungen,
                             gesamtpreis=gesamtpreis)
    
    # POST-Methode für neue Bestellungen
    try:
        if 'current_table' not in session:
            return jsonify({'success': False, 'message': 'Keine Tischnummer ausgewählt'}), 400
            
        data = request.get_json()
        if not data or 'orders' not in data:
            return jsonify({'success': False, 'message': 'Keine Bestellungen empfangen'}), 400

        orders = data['orders']
        if not isinstance(orders, list) or not orders:
            return jsonify({'success': False, 'message': 'Ungültiges Bestellungsformat'}), 400

        tisch = str(session['current_table'])
        logger.info(f"Neue Bestellung für Tisch {tisch}: {len(orders)} Artikel")

        # Lade aktuelle Produkte
        try:
            with open(Config.PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                products = json.load(f)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Produkte: {str(e)}")
            return jsonify({'success': False, 'message': 'Fehler beim Laden der Produkte'}), 500

        # Validiere und verarbeite Bestellungen
        valid_orders = []
        for order in orders:
            if not isinstance(order, dict) or 'produkt' not in order or 'menge' not in order:
                continue

            produkt_id = str(order['produkt'])
            produkt = next((p for p in products if str(p['id']) == produkt_id), None)
            if not produkt:
                logger.warning(f"Produkt nicht gefunden: {produkt_id}")
                continue

            try:
                menge = int(order['menge'])
                if menge <= 0 or menge > 99:  # Maximale Bestellmenge
                    logger.warning(f"Ungültige Menge für Produkt {produkt_id}: {menge}")
                    continue
            except (ValueError, TypeError):
                logger.warning(f"Ungültige Menge für Produkt {produkt_id}")
                continue

            bestellung = {
                'id': len(bestellungen) + 1,
                'tisch': tisch,
                'produkt': produkt['name'],
                'menge': menge,
                'kommentar': str(order.get('kommentar', '')).strip()[:200],
                'kategorie': produkt['kategorie'],
                'price': produkt.get('price', 0.0),
                'zeitpunkt': datetime.now().isoformat(),
                'status': 'neu'
            }
            valid_orders.append(bestellung)
            logger.info(f"Bestellung validiert: {bestellung}")

        if not valid_orders:
            return jsonify({'success': False, 'message': 'Keine gültigen Bestellungen'}), 400

        # Füge Bestellungen hinzu und speichere
        bestellungen.extend(valid_orders)
        if atomic_save(Config.ORDERS_FILE, bestellungen):
            logger.info(f"{len(valid_orders)} Bestellungen für Tisch {tisch} gespeichert")
            
            # Starte den Druckprozess asynchron
            def async_print_orders():
                try:
                    check_and_print_orders(tisch)
                except Exception as e:
                    logger.error(f"Fehler beim asynchronen Drucken für Tisch {tisch}: {str(e)}")
            
            # Starte den Druckprozess in einem separaten Thread
            print_thread = threading.Thread(target=async_print_orders)
            print_thread.daemon = True
            print_thread.start()
            
            # Antworte sofort dem Client
            return jsonify({
                'success': True,
                'message': f'{len(valid_orders)} Bestellungen erfolgreich gespeichert und zum Drucken in Warteschlange eingereiht'
            })
        else:
            logger.error("Fehler beim Speichern der Bestellungen")
            return jsonify({'success': False, 'message': 'Fehler beim Speichern der Bestellungen'}), 500
            
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei der Bestellungsverarbeitung: {str(e)}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

def calculate_order_total(order):
    """Berechnet den Gesamtpreis einer Bestellung."""
    produkt = next((p for p in produkte if p['name'] == order['produkt']), None)
    if produkt and 'price' in produkt:
        return float(produkt['price']) * order['menge']
    return 0.0

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        logger.info("Admin-Login-Versuch")
        
        if not password:
            logger.warning("Login-Versuch ohne Passwort")
            flash('Bitte geben Sie ein Passwort ein')
            return render_template('admin_login.html')
            
        if check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password):
            session.clear()  # Lösche alte Session-Daten
            session['is_admin'] = True
            session.permanent = True
            logger.info("Admin-Login erfolgreich")
            logger.debug(f"Session nach Login: {dict(session)}")
            return redirect(url_for('admin_panel'))
            
        logger.warning("Admin-Login fehlgeschlagen - falsches Passwort")
        flash('Falsches Passwort')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    if session.get('is_admin'):
        logger.info("Admin-Logout")
    session.pop('is_admin', None)
    return redirect(url_for('table_selection'))

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_panel():
    """Admin-Panel mit Performance-Metriken und Bestellungsverwaltung."""
    global kategorien, produkte, bestellungen  # Globale Variablen deklarieren
    
    if not session.get('is_admin'):
        logger.warning("Zugriff auf Admin-Panel ohne Admin-Rechte")
        flash('Bitte als Admin einloggen')
        return redirect(url_for('admin_login'))
        
    logger.info("Admin-Panel aufgerufen")
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'add_kategorie':
                name = request.form.get('kategorie_name', '').strip()
                if name and name not in [k['name'] for k in kategorien]:
                    kategorien.append({'id': len(kategorien) + 1, 'name': name})
                    save_data(Config.CATEGORIES_FILE, kategorien)
                    # Aktualisiere globale Variable
                    kategorien = load_data(Config.CATEGORIES_FILE)
                    flash('Kategorie hinzugefügt')
                    
            elif action == 'add_produkt':
                name = request.form.get('produkt_name', '').strip()
                kategorie_id = int(request.form.get('kategorie_id', 0))
                price = float(request.form.get('price', 0.0))
                if name and kategorie_id and any(k['id'] == kategorie_id for k in kategorien):
                    produkte.append({
                        'id': len(produkte) + 1,
                        'name': name,
                        'kategorie': kategorie_id,
                        'price': price
                    })
                    save_data(Config.PRODUCTS_FILE, produkte)
                    # Aktualisiere globale Variable
                    produkte = load_data(Config.PRODUCTS_FILE)
                    flash('Produkt hinzugefügt')
                    
            elif action == 'update_price':
                produkt_id = int(request.form.get('produkt_id', 0))
                new_price = float(request.form.get('price', 0.0))
                if produkt_id:
                    for produkt in produkte:
                        if produkt['id'] == produkt_id:
                            produkt['price'] = new_price
                            break
                    save_data(Config.PRODUCTS_FILE, produkte)
                    # Aktualisiere globale Variable
                    produkte = load_data(Config.PRODUCTS_FILE)
                    flash('Preis aktualisiert')
                    
            elif action == 'delete_kategorie':
                kategorie_id = int(request.form.get('kategorie_id', 0))
                if kategorie_id:
                    kategorien[:] = [k for k in kategorien if k['id'] != kategorie_id]
                    produkte[:] = [p for p in produkte if p['kategorie'] != kategorie_id]
                    save_data(Config.CATEGORIES_FILE, kategorien)
                    save_data(Config.PRODUCTS_FILE, produkte)
                    # Aktualisiere globale Variablen
                    kategorien = load_data(Config.CATEGORIES_FILE)
                    produkte = load_data(Config.PRODUCTS_FILE)
                    flash('Kategorie gelöscht')
                    
            elif action == 'delete_produkt':
                produkt_id = int(request.form.get('produkt_id', 0))
                if produkt_id:
                    produkte[:] = [p for p in produkte if p['id'] != produkt_id]
                    save_data(Config.PRODUCTS_FILE, produkte)
                    # Aktualisiere globale Variable
                    produkte = load_data(Config.PRODUCTS_FILE)
                    flash('Produkt gelöscht')
                    
            return redirect(url_for('admin_panel'))
            
        except Exception as e:
            logger.error(f"Fehler im Admin-Panel: {str(e)}")
            flash('Ein Fehler ist aufgetreten')
            return redirect(url_for('admin_panel'))
        
    # Hole Performance-Metriken
    metrics = performance_metrics.get_metrics()
    
    # Lade aktuelle Daten
    kategorien = load_data(Config.CATEGORIES_FILE)
    produkte = load_data(Config.PRODUCTS_FILE)
    bestellungen = load_data(Config.ORDERS_FILE)
    
    return render_template('admin_panel.html', 
                         kategorien=kategorien, 
                         produkte=produkte, 
                         bestellungen=bestellungen,
                         metrics=metrics,
                         current_time=datetime.now())

@app.route('/admin/metrics')
@admin_required
def get_metrics():
    """Gibt aktuelle Performance-Metriken zurück."""
    return jsonify(performance_metrics.get_metrics())

@app.route('/admin/check-status')
def check_admin_status():
    return jsonify({'is_admin': session.get('is_admin', False)})

@app.route('/delete-order/<int:order_id>', methods=['POST'])
@admin_required
def delete_order(order_id):
    try:
        global bestellungen
        bestellungen = [b for b in bestellungen if b['id'] != order_id]
        save_data(Config.ORDERS_FILE, bestellungen)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Bestellung: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen'})

@app.route('/update-order-status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['neu', 'erledigt', 'archiviert']:
            return jsonify({'success': False, 'message': 'Ungültiger Status'})
            
        for bestellung in bestellungen:
            if bestellung['id'] == order_id:
                bestellung['status'] = new_status
                if new_status == 'erledigt':
                    bestellung['erledigt_um'] = datetime.now().isoformat()
                logger.info(f"Bestellung {order_id} Status aktualisiert zu {new_status}")
                break
                
        save_data(Config.ORDERS_FILE, bestellungen)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Bestellstatus: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren'})

@app.route('/add-comment/<int:order_id>', methods=['POST'])
def add_comment(order_id):
    """Fügt einen Kommentar zu einer Bestellung hinzu."""
    try:
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Keine Berechtigung'}), 403
            
        data = request.get_json()
        if not data or 'comment' not in data:
            return jsonify({'success': False, 'message': 'Kein Kommentar angegeben'}), 400
            
        comment = str(data.get('comment', '')).strip()[:200]  # Begrenze auf 200 Zeichen
        
        # Finde die Bestellung
        bestellung = next((b for b in bestellungen if b['id'] == order_id), None)
        if not bestellung:
            return jsonify({'success': False, 'message': 'Bestellung nicht gefunden'}), 404
            
        # Aktualisiere den Kommentar
        bestellung['kommentar'] = comment
        logger.info(f"Kommentar für Bestellung {order_id} aktualisiert: {comment}")
        
        # Speichere die Änderung
        if save_data(Config.ORDERS_FILE, bestellungen):
            # Sende Update über WebSocket
            socketio.emit('comment_updated', {
                'order_id': order_id,
                'comment': comment
            }, broadcast=True)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Speichern'}), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@socketio.on('comment_update')
def handle_comment_update(data):
    """Behandelt Kommentar-Updates für Bestellungen über WebSocket."""
    try:
        if not session.get('is_admin'):
            emit('error', {'message': 'Keine Berechtigung'})
            return
            
        order_id = data.get('order_id')
        comment = str(data.get('comment', '')).strip()[:200]  # Begrenze auf 200 Zeichen
        
        if not order_id:
            emit('error', {'message': 'Keine Bestellungs-ID angegeben'})
            return
            
        # Finde die Bestellung
        bestellung = next((b for b in bestellungen if b['id'] == order_id), None)
        if not bestellung:
            emit('error', {'message': 'Bestellung nicht gefunden'})
            return
            
        # Aktualisiere den Kommentar
        bestellung['kommentar'] = comment
        logger.info(f"Kommentar für Bestellung {order_id} über WebSocket aktualisiert: {comment}")
        
        # Speichere die Änderung
        if save_data(Config.ORDERS_FILE, bestellungen):
            # Sende Update an alle Clients
            emit('comment_updated', {
                'order_id': order_id,
                'comment': comment
            }, broadcast=True)
        else:
            emit('error', {'message': 'Fehler beim Speichern des Kommentars'})
            
    except Exception as e:
        logger.error(f"Fehler beim WebSocket-Kommentar-Update: {str(e)}")
        emit('error', {'message': 'Interner Serverfehler'})

@app.route('/order-management/<order_type>', methods=['GET'])
@admin_required
def order_management(order_type):
    """Seite für die detaillierte Bestellungsverwaltung, getrennt nach Essen und Trinken."""
    if order_type not in ['essen', 'trinken']:
        return redirect(url_for('admin_panel'))
        
    logger.info(f"Bestellungsverwaltung aufgerufen für {order_type}")
    filtered_orders = get_orders_by_type(order_type)
    return render_template('order_management.html', 
                         kategorien=kategorien, 
                         produkte=produkte, 
                         bestellungen=filtered_orders,
                         order_type=order_type)

@socketio.on('connect')
def handle_connect():
    """Behandelt neue WebSocket-Verbindungen."""
    if session.get('is_admin'):
        logger.info("Admin-WebSocket-Verbindung hergestellt")
        emit('connection_response', {'data': 'Verbunden'})
    else:
        logger.warning("Nicht-Admin versucht WebSocket-Verbindung herzustellen")
        return False

@socketio.on('order_status_update')
def handle_order_status_update(data):
    """Behandelt Status-Updates von Bestellungen."""
    if not session.get('is_admin'):
        return
        
    try:
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if new_status not in ['neu', 'erledigt', 'archiviert']:
            return
            
        for bestellung in bestellungen:
            if bestellung['id'] == order_id:
                bestellung['status'] = new_status
                if new_status == 'erledigt':
                    bestellung['erledigt_um'] = datetime.now().isoformat()
                logger.info(f"Bestellung {order_id} Status aktualisiert zu {new_status}")
                break
                
        save_data(Config.ORDERS_FILE, bestellungen)
        
        # Sende Update an alle verbundenen Clients
        emit('order_updated', {
            'order_id': order_id,
            'status': new_status,
            'erledigt_um': bestellung.get('erledigt_um')
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Fehler beim WebSocket-Status-Update: {str(e)}")
        emit('error', {'message': 'Fehler beim Aktualisieren des Status'})

@socketio.on('product_done_update')
def handle_product_done_update(data):
    """Behandelt Updates für einzelne Produkte in Bestellungen."""
    if not session.get('is_admin'):
        return
        
    try:
        order_id = data.get('order_id')
        product_index = data.get('product_index')
        is_done = data.get('is_done')
        
        for bestellung in bestellungen:
            if bestellung['id'] == order_id:
                if 'erledigte_produkte' not in bestellung:
                    bestellung['erledigte_produkte'] = []
                    
                if is_done and product_index not in bestellung['erledigte_produkte']:
                    bestellung['erledigte_produkte'].append(product_index)
                elif not is_done and product_index in bestellung['erledigte_produkte']:
                    bestellung['erledigte_produkte'].remove(product_index)
                    
                logger.info(f"Produkt {product_index} in Bestellung {order_id} Status aktualisiert")
                break
                
        save_data(Config.ORDERS_FILE, bestellungen)
        
        # Sende Update an alle verbundenen Clients
        emit('product_updated', {
            'order_id': order_id,
            'product_index': product_index,
            'is_done': is_done
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Fehler beim WebSocket-Produkt-Update: {str(e)}")
        emit('error', {'message': 'Fehler beim Aktualisieren des Produktstatus'})

@socketio.on('order_delete')
def handle_order_delete(data):
    """Behandelt das Löschen von Bestellungen."""
    if not session.get('is_admin'):
        return
        
    try:
        order_id = data.get('order_id')
        global bestellungen
        bestellungen = [b for b in bestellungen if b['id'] != order_id]
        save_data(Config.ORDERS_FILE, bestellungen)
        
        # Sende Update an alle verbundenen Clients
        emit('order_deleted', {
            'order_id': order_id
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f"Fehler beim WebSocket-Bestellung-Löschen: {str(e)}")
        emit('error', {'message': 'Fehler beim Löschen der Bestellung'})

@app.route('/admin/cleanup-orders', methods=['POST'])
@admin_required
def cleanup_orders():
    """Löscht alle erledigten Bestellungen."""
    try:
        delete_completed_orders()
        return jsonify({'success': True, 'message': 'Erledigte Bestellungen wurden gelöscht'})
    except Exception as e:
        logger.error(f"Fehler beim Aufräumen der Bestellungen: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Bestellungen'})

@app.route('/admin/receipt-template', methods=['GET', 'POST'])
@admin_required
def receipt_template():
    """Admin-Seite für die Bon-Gestaltung."""
    if request.method == 'POST':
        try:
            template = {
                'header': {
                    'text': request.form.get('header_text', ''),
                    'align': request.form.get('header_align', 'center'),
                    'font': request.form.get('header_font', 'a'),
                    'width': int(request.form.get('header_width', 1)),
                    'height': int(request.form.get('header_height', 1))
                },
                'footer': {
                    'text': request.form.get('footer_text', ''),
                    'align': request.form.get('footer_align', 'center'),
                    'font': request.form.get('footer_font', 'a'),
                    'width': int(request.form.get('footer_width', 1)),
                    'height': int(request.form.get('footer_height', 1))
                },
                'separator': request.form.get('separator', '=' * 32),
                'order_format': {
                    'product': request.form.get('product_format', '{menge}x {produkt}'),
                    'price': request.form.get('price_format', '   {menge} x {price:.2f}€ = {total:.2f}€'),
                    'comment': request.form.get('comment_format', '   Kommentar: {comment}'),
                    'time': request.form.get('time_format', '   Zeit: {time}')
                }
            }
            
            if save_receipt_template(template):
                flash('Bon-Template erfolgreich gespeichert')
            else:
                flash('Fehler beim Speichern des Templates')
                
            return redirect(url_for('receipt_template'))
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Bon-Templates: {str(e)}")
            flash('Fehler beim Speichern des Templates')
            return redirect(url_for('receipt_template'))
    
    template = load_receipt_template()
    return render_template('receipt_template.html', template=template)

if __name__ == '__main__':
    # Stelle sicher, dass alle notwendigen Dateien existieren
    for file_path in [Config.CATEGORIES_FILE, Config.PRODUCTS_FILE, Config.ORDERS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    # Starte den Drucker-Worker beim Programmstart
    if not start_printer_worker():
        logger.error("Konnte Drucker-Worker nicht starten - Programm wird beendet")
        sys.exit(1)
    
    # Konfiguriere den Server für Produktionsumgebung
    if os.environ.get('FLASK_ENV') == 'production':
        # Verwende Gunicorn als WSGI-Server
        from gunicorn.app.base import BaseApplication
        
        class FlaskApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.application = app
                self.options = options or {}
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)

            def load(self):
                return self.application

        options = {
            'bind': '0.0.0.0:5000',
            'workers': Config.WORKERS,
            'worker_class': 'sync',  # Verwende sync statt gevent
            'timeout': Config.TIMEOUT,
            'keepalive': Config.KEEPALIVE,
            'max_requests': Config.MAX_REQUESTS,
            'max_requests_jitter': Config.MAX_REQUESTS_JITTER,
            'worker_connections': 1000,
            'graceful_timeout': 30,
            'preload_app': True
        }
        
        FlaskApplication(app, options).run()
    else:
        # Entwicklungsserver
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,  # Zurück auf 5000, da Nginx den Port 80 übernimmt
            debug=False,
            use_reloader=False  # Deaktiviere Reloader für bessere Performance
        )
