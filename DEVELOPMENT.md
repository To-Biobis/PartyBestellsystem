# Development Guide

## Modulare Architektur

Das PartyBestellsystem wurde in Version 2.0 komplett refaktoriert und verwendet jetzt eine modulare Architektur für bessere Wartbarkeit und Erweiterbarkeit.

## Verzeichnisstruktur

```
PartyBestellsystem/
├── src/                    # Hauptquellcode
│   ├── config/            # Konfigurationsverwaltung
│   │   ├── __init__.py
│   │   └── settings.py    # Config-Klasse mit allen Einstellungen
│   │
│   ├── database/          # Datenbank-Layer
│   │   ├── __init__.py
│   │   └── storage.py     # DataStorage für atomare Speicheroperationen
│   │
│   ├── printer/           # Druckerverwaltung
│   │   ├── __init__.py
│   │   ├── manager.py     # PrinterManager (Singleton)
│   │   └── queue_manager.py  # PrintQueueManager für asynchrones Drucken
│   │
│   ├── orders/            # Bestellungslogik
│   │   ├── __init__.py
│   │   ├── manager.py     # OrderManager für Bestellungsverwaltung
│   │   └── formatter.py   # OrderFormatter für Druckformatierung
│   │
│   ├── routes/            # Flask-Routes
│   │   ├── __init__.py
│   │   ├── main_routes.py        # Hauptroutes (Tischauswahl, etc.)
│   │   ├── admin_routes.py       # Admin-Interface
│   │   ├── order_routes.py       # Bestellungsverarbeitung
│   │   └── websocket_handlers.py # WebSocket-Events
│   │
│   ├── utils/             # Hilfsfunktionen
│   │   ├── __init__.py
│   │   ├── thread_safe.py    # Thread-sichere Datenstrukturen
│   │   └── logging_config.py # Logging-Setup
│   │
│   └── app.py             # Hauptanwendung
│
├── templates/             # Jinja2-Templates
├── data/                  # JSON-Datenbank
├── run.py                 # Einstiegspunkt
├── test_modules.py        # Modultests
└── install-rpi.sh         # Installationsskript
```

## Module im Detail

### 1. Config Module (`src/config/`)

**Verantwortlichkeit:** Zentrale Konfigurationsverwaltung

```python
from src.config import Config

# Zugriff auf Konfiguration
print(Config.DATA_DIR)
print(Config.PRINTER_VENDOR_ID)
```

**Wichtige Einstellungen:**
- `DATA_DIR`: Verzeichnis für Datendateien
- `PRINTER_*`: Druckerkonfiguration
- `LOG_*`: Logging-Einstellungen
- `SECRET_KEY`: Flask Session-Secret

### 2. Database Module (`src/database/`)

**Verantwortlichkeit:** Datenpersistenz mit atomaren Operationen und Backups

```python
from src.database import DataStorage

storage = DataStorage(data_dir, backup_dir, max_backups=5)

# Daten laden
data = storage.load_data('file.json', default=[])

# Daten speichern (atomar)
storage.save_data('file.json', data)
```

**Features:**
- Atomare Schreiboperationen (verhindert Datenverlust)
- Automatische Backups
- Backup-Wiederherstellung bei Korruption
- Thread-sicher

### 3. Printer Module (`src/printer/`)

**Verantwortlichkeit:** Druckerverwaltung mit sofortigem Druck

#### PrinterManager (Singleton)
```python
from src.printer import PrinterManager

manager = PrinterManager.get_instance(vendor_id, product_id)
printer = manager.get_printer()
```

**Features:**
- Singleton-Pattern für eine Druckerinstanz
- Automatische Verbindungsverwaltung
- Fehlertolerante Verbindung mit Fallback-Endpunkten

#### PrintQueueManager
```python
from src.printer import PrintQueueManager

queue_manager = PrintQueueManager(printer_manager)
queue_manager.start_worker()

# Druckauftrag hinzufügen
queue_manager.add_print_job(content, job_id, callback)
```

**Features:**
- Asynchrone Druckverarbeitung
- **SOFORTIGER Druck** ohne künstliche Verzögerungen
- Automatische Wiederholungen bei Fehlern
- Callback-System für Status-Updates

### 4. Orders Module (`src/orders/`)

**Verantwortlichkeit:** Bestellungslogik und Formatierung

#### OrderManager
```python
from src.orders import OrderManager

manager = OrderManager(storage, products_file, categories_file, orders_file)

# Bestellung erstellen
order = manager.create_order(table, product_id, quantity, comment)

# Bestellungen filtern
new_orders = manager.get_new_orders_by_table('1')
grouped = manager.group_orders_by_category(orders)
```

**Features:**
- CRUD-Operationen für Bestellungen
- Status-Verwaltung (neu, in_druck, erledigt)
- Kategoriebasierte Gruppierung
- Preisberechnungen

#### OrderFormatter
```python
from src.orders import OrderFormatter

formatter = OrderFormatter(paper_width=32)
content = formatter.format_orders_for_category(table, category_name, orders)
```

**Features:**
- ESC/POS-kompatible Formatierung
- Kategoriebasierte Bons
- Flexible Template-Unterstützung

### 5. Routes Module (`src/routes/`)

**Verantwortlichkeit:** HTTP-Routes und WebSocket-Handler

Die Routes sind nach Funktionalität aufgeteilt:

- `main_routes.py`: Tischauswahl, Bestellseite
- `admin_routes.py`: Admin-Interface, Verwaltung
- `order_routes.py`: Bestellungsverarbeitung mit sofortigem Druck
- `websocket_handlers.py`: Echtzeit-Updates via SocketIO

### 6. Utils Module (`src/utils/`)

**Verantwortlichkeit:** Gemeinsam genutzte Hilfsfunktionen

```python
from src.utils import ThreadSafeDict, setup_logging

# Thread-sicheres Dictionary
safe_dict = ThreadSafeDict()
safe_dict.set('key', 'value')
value = safe_dict.get('key')
```

## Entwicklungsworkflow

### 1. Lokale Entwicklung

```bash
# Virtual Environment aktivieren
source .venv/bin/activate

# Anwendung starten
python3 run.py

# Oder direkt
python3 src/app.py
```

### 2. Tests ausführen

```bash
# Modultests
python3 test_modules.py

# Manuelles Testing
# 1. Starte die Anwendung
# 2. Öffne http://localhost:5000
# 3. Teste Bestellungen und Admin-Interface
```

### 3. Neues Feature hinzufügen

#### Beispiel: Neues Modul für Statistiken

1. **Modul erstellen:**
```bash
mkdir -p src/statistics
touch src/statistics/__init__.py
touch src/statistics/analyzer.py
```

2. **Code schreiben:**
```python
# src/statistics/analyzer.py
class StatisticsAnalyzer:
    def __init__(self, order_manager):
        self.order_manager = order_manager
    
    def get_daily_stats(self):
        # Implementierung
        pass
```

3. **In App integrieren:**
```python
# src/app.py
from src.statistics import StatisticsAnalyzer

stats_analyzer = StatisticsAnalyzer(order_manager)
```

4. **Routes hinzufügen:**
```python
# src/routes/stats_routes.py
def register_routes(app, stats_analyzer):
    @app.route('/api/statistics')
    def get_statistics():
        return jsonify(stats_analyzer.get_daily_stats())
```

### 4. Debugging

```bash
# Logging-Level erhöhen
# In src/config/settings.py:
LOG_LEVEL = logging.DEBUG

# Logs in Echtzeit ansehen
tail -f app.log

# Auf Raspberry Pi:
sudo journalctl -u bestellungssystem -f
```

## Best Practices

### 1. Modularität
- Jedes Modul hat eine klare Verantwortlichkeit
- Keine zirkulären Importe
- Abhängigkeiten werden über Konstruktor injiziert

### 2. Thread-Sicherheit
- Verwende `ThreadSafeDict` für gemeinsam genutzte Daten
- Locks für kritische Abschnitte
- Keine globalen Variablen ohne Synchronisation

### 3. Fehlerbehandlung
- Immer try-except für externe Operationen
- Aussagekräftige Fehlermeldungen
- Logging für alle Fehler

### 4. Testing
- Teste jedes neue Modul
- Verwende Mocks für externe Abhängigkeiten
- Teste Edge Cases

### 5. Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detaillierte Info für Debugging")
logger.info("Normale Operation")
logger.warning("Warnung, aber kein Fehler")
logger.error("Fehler aufgetreten")
```

## Drucksystem

### Sofortiger Druck

Das neue Drucksystem druckt **sofort** ohne künstliche Verzögerungen:

```python
# Alte Version (mit Timer und Verzögerungen)
timer = threading.Timer(30.0, print_orders)  # ❌ 30 Sekunden Wartezeit

# Neue Version (sofortiger Druck)
print_queue_manager.add_print_job(content, job_id, callback)  # ✓ Sofort
```

### Callback-System

```python
def print_callback(success, job_id):
    if success:
        # Markiere als gedruckt
        order_manager.update_order_status(order_id, 'erledigt')
    else:
        # Fehler - setze zurück
        order_manager.update_order_status(order_id, 'neu')

print_queue_manager.add_print_job(content, job_id, print_callback)
```

## Status-Indikatoren in der Web-View

### Implementierung

Die Web-View zeigt jetzt Echtzeit-Status an:

1. **Status-Zusammenfassung**: Zeigt Anzahl der neuen/druckenden/gedruckten Bestellungen
2. **Farbcodierte Bestellungen**: Gelb=Neu, Blau=Druckt, Grün=Gedruckt
3. **Status-Badges**: Icons für jeden Status
4. **Auto-Refresh**: Aktualisierung alle 10 Sekunden

### JavaScript-Funktionen

```javascript
// Status-Zusammenfassung aktualisieren
updateStatusSummary();

// Bestellliste aktualisieren
updateOrdersList();

// Automatische Updates
setInterval(updateOrdersList, 10000);
```

## Deployment

### Raspberry Pi

```bash
# Automatische Installation
sudo bash install-rpi.sh

# Service verwalten
sudo systemctl start bestellungssystem
sudo systemctl status bestellungssystem
sudo systemctl restart bestellungssystem
```

### Manuelle Installation

Siehe README.md für detaillierte Anweisungen.

## Fehlerbehebung

### Häufige Probleme

1. **Import-Fehler**: Stelle sicher, dass PYTHONPATH gesetzt ist
2. **Drucker-Fehler**: Prüfe USB-Berechtigungen und Vendor/Product IDs
3. **Port belegt**: Ändere Port in Config oder beende anderen Prozess

### Debug-Modus

```python
# In run.py oder src/app.py:
socketio.run(app, debug=True)  # Nur für Entwicklung!
```

## Weitere Informationen

- Siehe README.md für Benutzer-Dokumentation
- Siehe install-rpi.sh für Deployment-Details
- GitHub Issues für Bug-Reports und Feature-Requests
