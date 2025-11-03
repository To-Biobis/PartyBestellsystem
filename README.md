# PartyBestellsystem

Ein modernes, zuverlässiges Bestellsystem für Gastronomie und Events mit automatischem Druck.

## Features

- 🍽️ Tischbasiertes Bestellsystem
- 🖨️ Sofortiger automatischer Druck (keine künstlichen Verzögerungen)
- 📊 Kategoriebasierte Organisation
- 👨‍💼 Admin-Panel zur Verwaltung
- 🔄 Echtzeit-Updates via WebSocket
- 💾 Automatische Backups
- 🔒 Thread-sichere Datenverarbeitung
- 🏗️ Modulare, wartbare Architektur
- 🖨️ **NEU:** Multi-Drucker-Support mit Kategorie-Routing
- 📡 **NEU:** WiFi Access Point Modus für eigenständiges Netzwerk

## Neu in Version 2.0

- ✨ Komplett refaktorierte, modulare Codebase
- ⚡ Sofortiger Druck ohne Verzögerungen
- 🎯 Verbesserte Fehlerbehandlung und Logging
- 🔧 Einfachere Wartung und Erweiterbarkeit
- 📦 Klare Trennung der Verantwortlichkeiten
- 🚀 Optimierte Performance
- 🖨️ Modulares Multi-Drucker-System
- 📡 WiFi Access Point für eigenständigen Betrieb
- ⚙️ Verbessertes Installationsskript mit umfassender Fehlerbehandlung

## Architektur

```
PartyBestellsystem/
├── src/
│   ├── config/          # Konfigurationsverwaltung
│   ├── database/        # Datenpersistenz und Backups
│   ├── printer/         # Druckerverwaltung und Warteschlange
│   ├── orders/          # Bestellungslogik und Formatierung
│   ├── routes/          # Flask-Routes
│   ├── utils/           # Hilfsfunktionen
│   └── app.py           # Hauptanwendung
├── templates/           # HTML-Templates
├── data/                # JSON-Datenbank
└── install-rpi.sh       # Raspberry Pi Installationsskript
```

## Installation auf Raspberry Pi

### Schnellinstallation

```bash
# Repository klonen
git clone https://github.com/To-Biobis/PartyBestellsystem.git
cd PartyBestellsystem

# Installationsskript ausführen
sudo bash install-rpi.sh
```

Das Skript führt automatisch folgende Schritte aus:
1. System-Update
2. Installation aller Abhängigkeiten
3. Einrichtung der Python Virtual Environment
4. Konfiguration des systemd Service
5. Nginx-Konfiguration als Reverse Proxy
6. Automatischer Start der Anwendung

### Manuelle Installation

```bash
# System-Abhängigkeiten installieren
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git nginx libusb-1.0-0-dev

# Repository klonen
git clone https://github.com/To-Biobis/PartyBestellsystem.git
cd PartyBestellsystem

# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Datenverzeichnisse erstellen
mkdir -p data/backups

# USB-Berechtigungen für Drucker
sudo usermod -a -G lp $USER

# Anwendung starten
python3 src/app.py
```

## Konfiguration

### Umgebungsvariablen

```bash
# Admin-Passwort ändern
export ADMIN_PASSWORD="IhrSicheresPasswort"

# Secret Key für Sessions
export SECRET_KEY="IhrGeheimschlüssel"

# Produktionsumgebung
export FLASK_ENV="production"
```

### Drucker-Konfiguration

#### Einzelner Drucker

Die Standard-Drucker-Konfiguration befindet sich in `src/config/settings.py`:

```python
PRINTER_VENDOR_ID = 0x04b8  # Epson Vendor ID
PRINTER_PRODUCT_ID = 0x0e15  # TM-T20II Product ID
```

#### Mehrere Drucker (Multi-Printer Setup)

Für mehrere Drucker mit Kategorie-Routing siehe **[MULTI_PRINTER_SETUP.md](MULTI_PRINTER_SETUP.md)**

Beispiel-Konfiguration in `data/printer_config.json`:

```json
{
  "printers": [
    {
      "printer_id": "kitchen",
      "name": "Kitchen Printer",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Essen", "Desserts"],
      "enabled": true
    },
    {
      "printer_id": "bar",
      "name": "Bar Printer",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Getränke"],
      "enabled": true
    }
  ]
}
```

Unterstützte Drucker:
- Epson TM-T20II
- Epson TM-T88V
- Andere ESC/POS kompatible Drucker

### WiFi Access Point Einrichtung

Um das System als eigenständiges WiFi-Netzwerk zu betreiben:

```bash
sudo bash setup-wifi-ap.sh
```

Detaillierte Anleitung: **[WIFI_AP_SETUP.md](WIFI_AP_SETUP.md)**

Dies ermöglicht:
- Eigenständiges WiFi-Netzwerk ohne externe Router
- Direkte Verbindung von Bestellgeräten
- Multi-Drucker-Setups mit mehreren Raspberry Pis
- Mobile und Event-Einsätze

## Verwendung

### Bestellung aufgeben

1. Öffnen Sie `http://raspberry-pi-ip` im Browser
2. Geben Sie eine Tischnummer ein
3. Wählen Sie Produkte und Mengen
4. Klicken Sie auf "Bestellen"
5. Die Bestellung wird sofort gedruckt

### Admin-Panel

1. Navigieren Sie zu `http://raspberry-pi-ip/admin/login`
2. Melden Sie sich mit dem Admin-Passwort an (Standard: admin123)
3. Verwalten Sie:
   - Kategorien
   - Produkte und Preise
   - Aktuelle Bestellungen
   - Bestellungsstatus

## Service-Verwaltung

```bash
# Service starten
sudo systemctl start bestellungssystem

# Service stoppen
sudo systemctl stop bestellungssystem

# Service neu starten
sudo systemctl restart bestellungssystem

# Service-Status prüfen
sudo systemctl status bestellungssystem

# Logs ansehen
sudo journalctl -u bestellungssystem -f

# Service beim Boot aktivieren
sudo systemctl enable bestellungssystem
```

## Entwicklung

### Lokale Entwicklung

```bash
# Virtual Environment aktivieren
source .venv/bin/activate

# Entwicklungsserver starten
python3 src/app.py
```

### Projektstruktur

- `src/config/`: Konfigurationseinstellungen
- `src/database/`: Datenbank-Layer mit Backup-Funktionalität
- `src/printer/`: Drucker-Manager und Print-Queue
- `src/orders/`: Bestellungslogik und Formatierung
- `src/routes/`: HTTP-Routes und WebSocket-Handler
- `src/utils/`: Hilfsfunktionen und Thread-Safe Strukturen

### Neue Module hinzufügen

1. Erstellen Sie ein neues Verzeichnis in `src/`
2. Fügen Sie `__init__.py` hinzu
3. Importieren Sie das Modul in `src/app.py`
4. Registrieren Sie Routes falls nötig

## Fehlerbehebung

### Drucker druckt nicht

```bash
# USB-Geräte auflisten
lsusb

# Drucker-Berechtigungen prüfen
groups

# Service-Logs prüfen
sudo journalctl -u bestellungssystem -n 50
```

### Anwendung startet nicht

```bash
# Logs ansehen
sudo journalctl -u bestellungssystem -n 50

# Manuell starten (für Debug)
cd /home/pi/PartyBestellsystem
source .venv/bin/activate
python3 src/app.py
```

### Port bereits belegt

```bash
# Prozess auf Port 5000 finden
sudo netstat -tulpn | grep 5000

# Prozess beenden
sudo kill -9 <PID>
```

## Backup und Wiederherstellung

Backups werden automatisch erstellt in `data/backups/`:

```bash
# Manuelles Backup erstellen
cp -r data data_backup_$(date +%Y%m%d_%H%M%S)

# Backup wiederherstellen
cp -r data_backup_20240101_120000/* data/
```

## Sicherheit

- Ändern Sie das Standard-Admin-Passwort
- Verwenden Sie einen starken SECRET_KEY
- Halten Sie das System aktualisiert
- Verwenden Sie HTTPS in Produktionsumgebungen

## Lizenz

MIT License - siehe LICENSE Datei

## Support

Bei Problemen oder Fragen:
1. Prüfen Sie die Logs
2. Erstellen Sie ein Issue auf GitHub
3. Konsultieren Sie die Dokumentation

## Mitwirken

Beiträge sind willkommen! Bitte:
1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch
3. Commiten Sie Ihre Änderungen
4. Erstellen Sie einen Pull Request

## Credits

Entwickelt für Gastronomie und Events mit Fokus auf Zuverlässigkeit und Benutzerfreundlichkeit.
