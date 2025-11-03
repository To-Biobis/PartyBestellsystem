# Upgrade Guide - Modulares System mit Multi-Drucker und WiFi AP

Dieser Guide erklärt die neuen Features und wie Sie diese nutzen können.

## Übersicht der Änderungen

### 1. Verbessertes Installationsskript

Das Installationsskript wurde komplett überarbeitet:

#### Neue Features:
- **Umfassende Fehlerprüfung**: Alle Schritte werden validiert
- **Detaillierte Fehlerberichterstattung**: Alle Fehler werden am Ende zusammengefasst
- **Farbcodierte Ausgaben**: Bessere Übersicht durch Farben
- **Keine Annahmen**: Script prüft explizit alle Abhängigkeiten
- **Modulare Konfiguration**: Unterstützt neue Multi-Drucker-Konfiguration

#### Verwendung:
```bash
sudo bash install-rpi.sh
```

Das Script zeigt am Ende eine Zusammenfassung aller Fehler und Warnungen.

### 2. Multi-Drucker-System

Das System unterstützt jetzt mehrere Drucker mit automatischem Kategorie-Routing.

#### Vorteile:
- **Getrennte Bereiche**: Z.B. Küche und Bar
- **Paralleler Druck**: Mehrere Bestellungen gleichzeitig
- **Flexibles Routing**: Kategorien zu Druckern zuweisen
- **Einfache Verwaltung**: JSON-basierte Konfiguration

#### Schnellstart:

1. **Konfigurationsdatei erstellen**: `data/printer_config.json`

```json
{
  "printers": [
    {
      "printer_id": "kitchen",
      "name": "Küchendrucker",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Essen", "Desserts"],
      "enabled": true
    },
    {
      "printer_id": "bar",
      "name": "Bar-Drucker",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Getränke"],
      "enabled": true
    }
  ]
}
```

2. **System neu starten**:
```bash
sudo systemctl restart bestellungssystem
```

3. **Testen**:
Bestellungen werden automatisch an den richtigen Drucker geroutet basierend auf der Kategorie.

#### Detaillierte Dokumentation:
Siehe **[MULTI_PRINTER_SETUP.md](MULTI_PRINTER_SETUP.md)** für:
- Komplette Konfigurationsoptionen
- USB-IDs finden
- Troubleshooting
- Erweiterte Setups

### 3. WiFi Access Point Modus

Der Raspberry Pi kann jetzt als eigenständiger WiFi Access Point fungieren.

#### Vorteile:
- **Kein Router benötigt**: Eigenständiges Netzwerk
- **Mobile Einsätze**: Perfekt für Events
- **Einfache Verbindung**: Direktes WLAN für Bestellgeräte
- **Multi-Pi-Setups**: Mehrere Pis im gleichen Netzwerk

#### Schnellstart:

1. **Setup ausführen**:
```bash
sudo bash setup-wifi-ap.sh
```

2. **Mit WLAN verbinden**:
- SSID: `PartyBestellsystem`
- Passwort: `party2024`

3. **Browser öffnen**:
- Adresse: `http://192.168.4.1`
- Oder: `http://partybestellung.local`

#### Anpassung:

Vor dem Setup-Script die Variablen bearbeiten:
```bash
nano setup-wifi-ap.sh
```

Ändern Sie:
- `SSID="IhrNetzwerkName"`
- `PASSWORD="IhrSicheresPasswort"`
- `IP_ADDRESS="192.168.4.1"`

#### Detaillierte Dokumentation:
Siehe **[WIFI_AP_SETUP.md](WIFI_AP_SETUP.md)** für:
- Manuelle Konfiguration
- Internet-Sharing
- Netzwerk-Topologien
- Troubleshooting
- Erweiterte Konfiguration

## Migration von älteren Versionen

### Von Version 2.0.x

Die neuen Features sind vollständig rückwärtskompatibel:

1. **Ohne Änderungen**: System funktioniert wie bisher mit einem Drucker
2. **Mit Multi-Drucker**: Erstellen Sie `data/printer_config.json` und starten neu
3. **Mit WiFi AP**: Führen Sie `setup-wifi-ap.sh` aus

### Beispiel-Migration

#### Vorher (einzelner Drucker):
```python
# In src/config/settings.py
PRINTER_VENDOR_ID = 0x04b8
PRINTER_PRODUCT_ID = 0x0e15
```

#### Nachher (mehrere Drucker):
```json
// In data/printer_config.json
{
  "printers": [
    {
      "printer_id": "default",
      "name": "Standard-Drucker",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": [],
      "enabled": true
    }
  ]
}
```

Leere `categories`-Array bedeutet: Drucker verarbeitet alle Kategorien (Standard-Verhalten).

## Neue Dateien und Verzeichnisse

```
PartyBestellsystem/
├── install-rpi.sh              # Verbessertes Installationsskript
├── setup-wifi-ap.sh            # Neues WiFi AP Setup-Script
├── MULTI_PRINTER_SETUP.md      # Multi-Drucker-Dokumentation
├── WIFI_AP_SETUP.md            # WiFi AP Dokumentation
├── UPGRADE_GUIDE.md            # Dieser Guide
├── test_install.sh             # Test-Script für Installation
├── data/
│   ├── printer_config.json     # Multi-Drucker-Konfiguration (wird erstellt)
│   └── printer_config.example.json  # Beispiel-Konfiguration
└── src/
    └── printer/
        ├── config.py           # Drucker-Konfigurations-Management
        ├── multi_manager.py    # Multi-Drucker-Manager
        └── multi_queue_manager.py  # Multi-Queue-Manager
```

## Testing

### Module testen:
```bash
python3 test_modules.py
```

### Installation testen:
```bash
./test_install.sh
```

### Drucker testen:
```python
from src.printer import PrinterConfigManager, MultiPrinterManager

config_manager = PrinterConfigManager('data/printer_config.json')
multi_manager = MultiPrinterManager(config_manager)

# Test alle Drucker
results = multi_manager.test_all_printers()
for printer_id, success in results.items():
    print(f"{printer_id}: {'✓' if success else '✗'}")
```

## Best Practices

### 1. Backup vor Änderungen
```bash
cp data/printer_config.json data/printer_config.json.backup
```

### 2. Schrittweise Migration
- Testen Sie neue Features in einer Testumgebung
- Ändern Sie Konfigurationen inkrementell
- Dokumentieren Sie Ihre Änderungen

### 3. Monitoring
- Prüfen Sie Logs: `sudo journalctl -u bestellungssystem -f`
- Überwachen Sie Druckerstatus im Admin-Panel
- Testen Sie jeden Drucker einzeln

### 4. Sicherheit
- Ändern Sie Standard-Passwörter (WiFi AP, Admin)
- Halten Sie das System aktualisiert
- Verwenden Sie starke Passwörter (min. 12 Zeichen)

## Troubleshooting

### Problem: Install-Script schlägt fehl

**Lösung**:
1. Prüfen Sie die Fehlerzusammenfassung am Ende
2. Beheben Sie gemeldete Fehler
3. Script erneut ausführen

Das Script ist idempotent - kann mehrfach ausgeführt werden.

### Problem: Multi-Drucker funktioniert nicht

**Lösung**:
1. Prüfen Sie `data/printer_config.json` auf Syntax-Fehler
2. Verifizieren Sie USB-IDs mit `lsusb`
3. Testen Sie jeden Drucker einzeln
4. Prüfen Sie Logs: `sudo journalctl -u bestellungssystem -n 50`

### Problem: WiFi AP startet nicht

**Lösung**:
1. Prüfen Sie ob WiFi-Hardware vorhanden ist: `iw dev`
2. Logs ansehen: `sudo journalctl -u hostapd -n 50`
3. Konfiguration testen: `sudo hostapd -d /etc/hostapd/hostapd.conf`
4. Anderen Kanal probieren (1, 6, oder 11)

### Problem: Kategorien werden nicht richtig geroutet

**Lösung**:
1. Kategorie-Namen müssen exakt übereinstimmen (Groß-/Kleinschreibung)
2. Prüfen Sie `data/printer_config.json`
3. Ein Drucker mit leerer `categories`-Liste ist Fallback
4. Service neu starten nach Konfigurations-Änderungen

## Support

### Dokumentation
- [README.md](README.md) - Hauptdokumentation
- [MULTI_PRINTER_SETUP.md](MULTI_PRINTER_SETUP.md) - Multi-Drucker-Details
- [WIFI_AP_SETUP.md](WIFI_AP_SETUP.md) - WiFi AP Details
- [QUICKSTART.md](QUICKSTART.md) - Schnelleinstieg

### Logs prüfen
```bash
# System-Service
sudo journalctl -u bestellungssystem -f

# WiFi AP
sudo journalctl -u hostapd -f
sudo journalctl -u dnsmasq -f

# Allgemeine System-Logs
sudo tail -f /var/log/syslog
```

### GitHub Issues
Bei Problemen:
1. Beschreiben Sie das Problem
2. Fügen Sie relevante Logs bei
3. Geben Sie Ihre Konfiguration an
4. Erwähnen Sie Raspberry Pi Modell und Python-Version

## Zusammenfassung

Die neuen Features machen das System:
- **Flexibler**: Multi-Drucker und eigenes WLAN
- **Robuster**: Bessere Fehlerbehandlung
- **Modularer**: Einfach erweiterbar
- **Professioneller**: Geeignet für komplexere Setups

Alle Features sind optional und rückwärtskompatibel. Sie können das System wie bisher mit einem Drucker betreiben oder die neuen Features nach Bedarf aktivieren.
