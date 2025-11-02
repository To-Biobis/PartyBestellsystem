# Migration Guide: Version 1.x zu 2.0

Dieser Leitfaden hilft Ihnen beim Upgrade von der alten monolithischen Version zur neuen modularen Version 2.0.

## Wichtige Änderungen

### 1. Projektstruktur

**Alt (Version 1.x):**
```
PartyBestellsystem/
├── app.py (1400+ Zeilen)
├── templates/
├── data/
└── requirements.txt
```

**Neu (Version 2.0):**
```
PartyBestellsystem/
├── src/                    # Modularer Quellcode
│   ├── config/
│   ├── database/
│   ├── printer/
│   ├── orders/
│   ├── routes/
│   └── app.py
├── run.py                  # Neuer Einstiegspunkt
├── templates/
├── data/
└── requirements.txt
```

### 2. Startmethode

**Alt:**
```bash
python3 app.py
```

**Neu:**
```bash
python3 run.py
# oder
python3 src/app.py
```

### 3. Drucksystem

#### Sofortiger Druck statt Timer

**Alt:**
- Bestellungen wurden 30 Sekunden gesammelt
- Künstliche Verzögerungen zwischen Druckvorgängen
- Timer-basiertes System

**Neu:**
- **Sofortiger Druck** beim Bestellen
- Keine künstlichen Verzögerungen
- Queue-basiertes System mit Callbacks

**Code-Beispiel Alt:**
```python
# Warte 30 Sekunden vor dem Drucken
timer = threading.Timer(30.0, check_and_print_orders, args=[tisch])
timer.start()

# Künstliche Verzögerungen im Druckprozess
time.sleep(0.5)  # Vor dem Drucken
time.sleep(0.5)  # Nach dem Drucken
```

**Code-Beispiel Neu:**
```python
# Sofortiger Druck
print_queue_manager.add_print_job(content, job_id, callback)

# Kein time.sleep() mehr - nur bei Wiederholungen nach Fehler
```

## Schritt-für-Schritt Migration

### Schritt 1: Backup erstellen

```bash
# Backup der Daten
cp -r data data_backup_$(date +%Y%m%d)

# Backup der gesamten Installation
cp -r /home/pi/PartyBestellsystem /home/pi/PartyBestellsystem_backup
```

### Schritt 2: Code aktualisieren

```bash
# Auf Raspberry Pi
cd /home/pi/PartyBestellsystem

# Aktuellen Stand pullen
git stash  # Falls lokale Änderungen vorhanden
git pull origin main

# Oder neu klonen:
cd /home/pi
git clone https://github.com/To-Biobis/PartyBestellsystem.git PartyBestellsystem_new
cd PartyBestellsystem_new
```

### Schritt 3: Dependencies installieren

```bash
# Virtual Environment neu erstellen
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt
```

### Schritt 4: Daten migrieren

Die Datenformate sind kompatibel - einfach kopieren:

```bash
# Wenn neue Installation
cp ../PartyBestellsystem/data/*.json data/

# Backups auch kopieren (optional)
cp -r ../PartyBestellsystem/data/backups/* data/backups/
```

### Schritt 5: Konfiguration anpassen

**Umgebungsvariablen setzen:**

```bash
# In ~/.bashrc oder in der Service-Datei
export SECRET_KEY="ihr-geheimer-schluessel"
export ADMIN_PASSWORD="ihr-neues-passwort"
```

**Oder in der systemd Service-Datei:**

```ini
[Service]
Environment="SECRET_KEY=ihr-geheimer-schluessel"
Environment="ADMIN_PASSWORD=ihr-neues-passwort"
```

### Schritt 6: Service aktualisieren

**Alte Service-Datei:**
```ini
ExecStart=/home/pi/PartyBestellsystem/.venv/bin/python3 /home/pi/PartyBestellsystem/app.py
```

**Neue Service-Datei:**
```ini
Environment="PYTHONPATH=/home/pi/PartyBestellsystem"
ExecStart=/home/pi/PartyBestellsystem/.venv/bin/python3 /home/pi/PartyBestellsystem/run.py
```

**Aktualisieren:**
```bash
sudo cp bestellungssystem.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart bestellungssystem
```

### Schritt 7: Testen

```bash
# Status prüfen
sudo systemctl status bestellungssystem

# Logs ansehen
sudo journalctl -u bestellungssystem -n 50

# Test-Bestellung durchführen
# 1. Browser öffnen: http://raspberry-pi-ip
# 2. Tisch auswählen
# 3. Bestellung aufgeben
# 4. Prüfen ob gedruckt wird
```

### Schritt 8: Automatisches Installations-Script (Empfohlen)

Am einfachsten ist die Verwendung des Installations-Scripts:

```bash
cd /home/pi/PartyBestellsystem
sudo bash install-rpi.sh
```

Dies erledigt automatisch:
- System-Updates
- Dependency-Installation
- Service-Konfiguration
- Nginx-Setup
- Automatischer Start

## Anpassungen von Custom Code

Falls Sie den Code angepasst haben, hier die Migrationspfade:

### Eigene Drucklogik

**Alt:**
```python
# In app.py direkt
def my_custom_print():
    printer = find_printer()
    printer.text("Custom")
```

**Neu:**
```python
# In src/printer/custom.py
from src.printer import PrinterManager

class CustomPrinter:
    def __init__(self, printer_manager):
        self.printer_manager = printer_manager
    
    def my_custom_print(self):
        printer = self.printer_manager.get_printer()
        if printer:
            printer.text("Custom")
```

### Eigene Routes

**Alt:**
```python
# In app.py
@app.route('/my-route')
def my_route():
    return "Custom"
```

**Neu:**
```python
# In src/routes/custom_routes.py
def register_routes(app):
    @app.route('/my-route')
    def my_route():
        return "Custom"

# In src/app.py
from src.routes import custom_routes
custom_routes.register_routes(app)
```

### Eigene Datenverarbeitung

**Alt:**
```python
# In app.py
def my_data_processing():
    with open('data/orders.json') as f:
        data = json.load(f)
```

**Neu:**
```python
# In src/orders/custom.py
from src.database import DataStorage

class CustomProcessor:
    def __init__(self, storage, order_manager):
        self.storage = storage
        self.order_manager = order_manager
    
    def my_data_processing(self):
        # Nutze order_manager statt direktem File-Zugriff
        orders = self.order_manager.orders
```

## Neue Features nutzen

### Status-Anzeige in der Web-View

Die neue Version zeigt automatisch:
- ⏳ Neue Bestellungen (gelb)
- 🖨️ Wird gedruckt (blau)
- ✓ Gedruckt (grün)

Keine Änderungen nötig - funktioniert automatisch!

### Sofortiges Drucken

**Vorher:** Bestellungen wurden 30 Sekunden gesammelt
**Jetzt:** Sofortiger Druck beim Bestellen

**Vorteile:**
- Schnellere Bearbeitung
- Keine verlorenen Bestellungen bei Absturz
- Bessere Übersichtlichkeit

### Verbesserte Fehlertoleranz

- Automatische Backups alle 1 Stunde
- Atomare Schreiboperationen (kein Datenverlust bei Absturz)
- Automatische Wiederherstellung aus Backups
- Besseres Logging

## Rollback (falls nötig)

Falls Probleme auftreten:

```bash
# Service stoppen
sudo systemctl stop bestellungssystem

# Auf alte Version zurück
cd /home/pi
mv PartyBestellsystem PartyBestellsystem_v2
mv PartyBestellsystem_backup PartyBestellsystem

# Service neu starten
sudo systemctl restart bestellungssystem
```

## Häufige Probleme

### Problem: "Module not found" Fehler

**Lösung:**
```bash
export PYTHONPATH=/home/pi/PartyBestellsystem
# Oder in Service-Datei setzen
```

### Problem: Drucker druckt nicht

**Prüfen:**
1. USB-Verbindung: `lsusb`
2. Berechtigungen: `groups` (sollte 'lp' enthalten)
3. Logs: `sudo journalctl -u bestellungssystem -n 50`

**Lösung:**
```bash
sudo usermod -a -G lp $USER
# Neuanmeldung oder Reboot erforderlich
```

### Problem: Port 5000 bereits belegt

**Prüfen:**
```bash
sudo netstat -tulpn | grep 5000
```

**Lösung:**
```bash
# Alten Prozess beenden
sudo kill -9 <PID>

# Oder in src/config/settings.py Port ändern
```

### Problem: Service startet nicht

**Logs prüfen:**
```bash
sudo journalctl -u bestellungssystem -n 50
sudo journalctl -u bestellungssystem -f  # Folge neuen Logs
```

**Häufige Ursachen:**
- Fehlende Dependencies: `pip install -r requirements.txt`
- Falsche Pfade in Service-Datei
- Berechtigungsprobleme: `chown -R pi:pi /home/pi/PartyBestellsystem`

## Support

Bei Fragen oder Problemen:
1. Prüfe die Logs: `sudo journalctl -u bestellungssystem -n 100`
2. Siehe DEVELOPMENT.md für technische Details
3. Erstelle ein Issue auf GitHub mit:
   - Fehlermeldung
   - Relevante Logs
   - Raspberry Pi Version
   - Python Version

## Vorteile der neuen Version

✅ **Sofortiger Druck** - Keine 30 Sekunden Wartezeit mehr  
✅ **Modularer Code** - Einfacher zu warten und erweitern  
✅ **Status-Anzeige** - Sehe auf einen Blick was gedruckt wurde  
✅ **Besseres Logging** - Einfachere Fehlersuche  
✅ **Atomare Operationen** - Kein Datenverlust bei Absturz  
✅ **Automatische Backups** - Daten sind sicher  
✅ **Test-Framework** - Qualitätssicherung  
✅ **Dokumentation** - README.md, DEVELOPMENT.md, MIGRATION.md  

Die Migration ist es wert! 🎉
