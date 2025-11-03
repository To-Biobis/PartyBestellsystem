#!/bin/bash
# Installation script for PartyBestellsystem on Raspberry Pi
# Usage: sudo bash install-rpi.sh
#
# This script assumes nothing is pre-installed and performs comprehensive checks

# Disable exit on error initially to collect all errors
set +e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error tracking
ERRORS=()
WARNINGS=()

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS+=("$1")
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ERRORS+=("$1")
}

log_step() {
    echo ""
    echo "======================================"
    echo "$1"
    echo "======================================"
}

# Function to check command availability
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# Function to display all errors and warnings
show_summary() {
    echo ""
    echo "======================================"
    echo "Installation Summary"
    echo "======================================"
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo "  - $warning"
        done
    fi
    
    if [ ${#ERRORS[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}Errors encountered:${NC}"
        for error in "${ERRORS[@]}"; do
            echo "  - $error"
        done
        echo ""
        echo "Installation completed with errors. Please review and fix the issues above."
        return 1
    else
        echo ""
        echo -e "${GREEN}✓ Installation completed successfully!${NC}"
        return 0
    fi
}

log_step "PartyBestellsystem Installation"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Script muss als root ausgeführt werden (sudo bash install-rpi.sh)"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="/home/$ACTUAL_USER/PartyBestellsystem"

log_info "Installation wird durchgeführt für Benutzer: $ACTUAL_USER"
log_info "Installationsverzeichnis: $INSTALL_DIR"

# Pre-installation checks
log_step "[1/12] Pre-Installation Checks"

# Check internet connectivity
log_info "Checking internet connectivity..."
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    log_warn "Keine Internetverbindung erkannt. Installation könnte fehlschlagen."
fi

# Check available disk space (need at least 500MB)
AVAILABLE_SPACE=$(df /home | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt 512000 ]; then
    log_error "Nicht genügend Speicherplatz. Benötigt: 500MB, Verfügbar: $((AVAILABLE_SPACE/1024))MB"
fi

# Check Python version
log_info "Checking Python availability..."
if ! check_command python3; then
    log_warn "Python3 nicht gefunden - wird installiert"
else
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python3 gefunden: Version $PYTHON_VERSION"
fi

# Update system
log_step "[2/12] System wird aktualisiert"
log_info "Aktualisiere Paketlisten..."
if ! apt-get update; then
    log_error "apt-get update fehlgeschlagen"
else
    log_info "Paketlisten aktualisiert"
fi

log_info "Aktualisiere System-Pakete..."
if ! apt-get upgrade -y; then
    log_warn "apt-get upgrade hat Warnungen/Fehler erzeugt"
else
    log_info "System-Pakete aktualisiert"
fi

# Install system dependencies
log_step "[3/12] Installiere System-Abhängigkeiten"

REQUIRED_PACKAGES=(
    "python3"
    "python3-pip"
    "python3-venv"
    "git"
    "nginx"
    "libusb-1.0-0-dev"
    "libjpeg-dev"
    "zlib1g-dev"
    "libfreetype6-dev"
    "liblcms2-dev"
    "libopenjp2-7-dev"
    "libtiff-dev"
)

log_info "Installiere benötigte Pakete..."
for package in "${REQUIRED_PACKAGES[@]}"; do
    log_info "Installiere $package..."
    if ! apt-get install -y "$package" 2>&1 | grep -v "is already the newest version"; then
        log_error "Installation von $package fehlgeschlagen"
    fi
done

# Verify critical packages are installed
log_info "Überprüfe installierte Pakete..."
MISSING_PACKAGES=()
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii  $package"; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    log_error "Folgende Pakete konnten nicht installiert werden: ${MISSING_PACKAGES[*]}"
fi

# Create installation directory
log_step "[4/12] Erstelle Installationsverzeichnis"
if [ ! -d "$INSTALL_DIR" ]; then
    log_info "Erstelle Verzeichnis $INSTALL_DIR..."
    if ! mkdir -p "$INSTALL_DIR"; then
        log_error "Konnte Installationsverzeichnis nicht erstellen: $INSTALL_DIR"
    else
        log_info "Installationsverzeichnis erstellt"
    fi
else
    log_info "Installationsverzeichnis existiert bereits"
fi

# Copy or clone repository
log_step "[5/12] Kopiere Anwendungsdateien"
if [ -d "/tmp/PartyBestellsystem" ]; then
    log_info "Kopiere von /tmp/PartyBestellsystem..."
    if ! cp -r /tmp/PartyBestellsystem/* "$INSTALL_DIR/"; then
        log_error "Fehler beim Kopieren der Dateien"
    else
        log_info "Dateien erfolgreich kopiert"
    fi
elif [ "$(basename $(pwd))" = "PartyBestellsystem" ]; then
    log_info "Kopiere aus aktuellem Verzeichnis..."
    if ! cp -r ./* "$INSTALL_DIR/"; then
        log_error "Fehler beim Kopieren der Dateien"
    else
        log_info "Dateien erfolgreich kopiert"
    fi
else
    log_error "PartyBestellsystem-Verzeichnis nicht gefunden"
    log_error "Bitte führen Sie dieses Skript aus dem PartyBestellsystem-Verzeichnis aus"
    log_error "oder klonen Sie das Repository nach /tmp/PartyBestellsystem"
fi

# Set ownership
log_info "Setze Berechtigungen..."
if ! chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR"; then
    log_error "Fehler beim Setzen der Berechtigungen"
else
    log_info "Berechtigungen gesetzt"
fi

# Create Python virtual environment
log_step "[6/12] Erstelle Python Virtual Environment"
cd "$INSTALL_DIR" || {
    log_error "Konnte nicht in Installationsverzeichnis wechseln"
    show_summary
    exit 1
}

log_info "Erstelle Virtual Environment..."
if ! sudo -u $ACTUAL_USER python3 -m venv .venv; then
    log_error "Fehler beim Erstellen des Virtual Environment"
else
    log_info "Virtual Environment erstellt"
fi

# Verify venv was created
if [ ! -f ".venv/bin/python3" ]; then
    log_error "Virtual Environment wurde nicht korrekt erstellt"
fi

# Install Python dependencies
log_step "[7/12] Installiere Python-Abhängigkeiten"

log_info "Aktualisiere pip..."
if ! sudo -u $ACTUAL_USER .venv/bin/pip install --upgrade pip 2>&1 | tee /tmp/pip_upgrade.log; then
    log_error "Fehler beim Aktualisieren von pip"
    log_error "Details in /tmp/pip_upgrade.log"
else
    log_info "pip aktualisiert"
fi

log_info "Installiere Python-Pakete aus requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt nicht gefunden!"
else
    if ! sudo -u $ACTUAL_USER .venv/bin/pip install -r requirements.txt 2>&1 | tee /tmp/pip_install.log; then
        log_error "Fehler beim Installieren der Python-Abhängigkeiten"
        log_error "Details in /tmp/pip_install.log"
    else
        log_info "Python-Abhängigkeiten installiert"
    fi
fi

# Verify critical Python packages
log_info "Überprüfe installierte Python-Pakete..."
CRITICAL_PACKAGES=("Flask" "python-escpos" "pyusb")
for package in "${CRITICAL_PACKAGES[@]}"; do
    if ! sudo -u $ACTUAL_USER .venv/bin/pip list | grep -i "$package" &> /dev/null; then
        log_error "Kritisches Python-Paket nicht installiert: $package"
    fi
done

# Create data directories
log_step "[8/12] Erstelle Datenverzeichnisse"
log_info "Erstelle data-Verzeichnis..."
if ! sudo -u $ACTUAL_USER mkdir -p "$INSTALL_DIR/data"; then
    log_error "Fehler beim Erstellen des data-Verzeichnisses"
else
    log_info "data-Verzeichnis erstellt"
fi

log_info "Erstelle backups-Verzeichnis..."
if ! sudo -u $ACTUAL_USER mkdir -p "$INSTALL_DIR/data/backups"; then
    log_error "Fehler beim Erstellen des backups-Verzeichnisses"
else
    log_info "backups-Verzeichnis erstellt"
fi

# Initialize data files if they don't exist
log_info "Initialisiere Datendateien..."
if [ ! -f "$INSTALL_DIR/data/categories.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/categories.json"
    log_info "categories.json erstellt"
fi
if [ ! -f "$INSTALL_DIR/data/products.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/products.json"
    log_info "products.json erstellt"
fi
if [ ! -f "$INSTALL_DIR/data/orders.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/orders.json"
    log_info "orders.json erstellt"
fi
if [ ! -f "$INSTALL_DIR/data/printer_config.json" ]; then
    echo '{"printers": []}' > "$INSTALL_DIR/data/printer_config.json"
    log_info "printer_config.json erstellt"
fi

if ! chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR/data"; then
    log_error "Fehler beim Setzen der Berechtigungen für data-Verzeichnis"
else
    log_info "Berechtigungen für data-Verzeichnis gesetzt"
fi

# Setup USB permissions for printer
log_step "[9/12] Konfiguriere USB-Berechtigungen für Drucker"
log_info "Füge Benutzer zur lp-Gruppe hinzu..."
if ! usermod -a -G lp $ACTUAL_USER; then
    log_error "Fehler beim Hinzufügen des Benutzers zur lp-Gruppe"
else
    log_info "Benutzer zur lp-Gruppe hinzugefügt"
fi

# Verify group membership
if groups $ACTUAL_USER | grep -q lp; then
    log_info "Gruppenmitgliedschaft verifiziert"
else
    log_error "Benutzer ist nicht in der lp-Gruppe"
fi

# Create systemd service file
log_step "[10/12] Erstelle systemd Service"
log_info "Erstelle Service-Datei..."
if ! cat > /etc/systemd/system/bestellungssystem.service << EOF
[Unit]
Description=PartyBestellsystem Service
After=network.target

[Service]
Type=simple
User=$ACTUAL_USER
Group=lp
WorkingDirectory=$INSTALL_DIR
Environment="FLASK_ENV=production"
Environment="FLASK_APP=src/app.py"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/.venv/bin/python3 $INSTALL_DIR/src/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
then
    log_error "Fehler beim Erstellen der Service-Datei"
else
    log_info "Service-Datei erstellt"
fi

# Verify service file
if [ ! -f "/etc/systemd/system/bestellungssystem.service" ]; then
    log_error "Service-Datei wurde nicht erstellt"
fi

# Configure nginx
log_step "[11/12] Konfiguriere nginx"
log_info "Erstelle nginx-Konfiguration..."
if ! cat > /etc/nginx/sites-available/bestellungssystem << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
EOF
then
    log_error "Fehler beim Erstellen der nginx-Konfiguration"
else
    log_info "nginx-Konfiguration erstellt"
fi

# Enable nginx site
log_info "Aktiviere nginx-Site..."
if ! ln -sf /etc/nginx/sites-available/bestellungssystem /etc/nginx/sites-enabled/; then
    log_error "Fehler beim Aktivieren der nginx-Site"
else
    log_info "nginx-Site aktiviert"
fi

if [ -f /etc/nginx/sites-enabled/default ]; then
    log_info "Deaktiviere Standard-Site..."
    rm -f /etc/nginx/sites-enabled/default
fi

# Test nginx configuration
log_info "Teste nginx-Konfiguration..."
if ! nginx -t 2>&1; then
    log_error "nginx-Konfiguration fehlerhaft"
else
    log_info "nginx-Konfiguration ist gültig"
fi

# Reload systemd and enable services
log_step "[12/12] Aktiviere und starte Services"
log_info "Lade systemd neu..."
if ! systemctl daemon-reload; then
    log_error "Fehler beim Neuladen von systemd"
else
    log_info "systemd neugeladen"
fi

log_info "Aktiviere bestellungssystem.service..."
if ! systemctl enable bestellungssystem; then
    log_error "Fehler beim Aktivieren des bestellungssystem.service"
else
    log_info "bestellungssystem.service aktiviert"
fi

log_info "Aktiviere nginx..."
if ! systemctl enable nginx; then
    log_error "Fehler beim Aktivieren von nginx"
else
    log_info "nginx aktiviert"
fi

# Start services
log_info "Starte nginx..."
if ! systemctl restart nginx; then
    log_error "Fehler beim Starten von nginx"
    log_error "Logs: journalctl -u nginx -n 20"
else
    log_info "nginx gestartet"
fi

log_info "Starte bestellungssystem..."
if ! systemctl restart bestellungssystem; then
    log_error "Fehler beim Starten des bestellungssystem"
    log_error "Logs: journalctl -u bestellungssystem -n 20"
else
    log_info "bestellungssystem gestartet"
fi

# Verify services are running
sleep 2
log_info "Überprüfe Service-Status..."
if ! systemctl is-active --quiet nginx; then
    log_error "nginx läuft nicht"
fi
if ! systemctl is-active --quiet bestellungssystem; then
    log_error "bestellungssystem läuft nicht"
fi

# Show summary
show_summary
INSTALL_SUCCESS=$?

echo ""
if [ $INSTALL_SUCCESS -eq 0 ]; then
    log_step "Installation erfolgreich abgeschlossen!"
    echo ""
    log_info "Die Anwendung wurde erfolgreich installiert und gestartet."
    echo ""
    echo "Nächste Schritte:"
    echo "1. Überprüfen Sie den Status: sudo systemctl status bestellungssystem"
    echo "2. Logs ansehen: sudo journalctl -u bestellungssystem -f"
    echo "3. Öffnen Sie einen Browser und navigieren Sie zu http://$(hostname -I | awk '{print $1}')"
    echo ""
    echo "Standard-Admin-Passwort: admin123"
    echo "WICHTIG: Ändern Sie das Passwort über die Umgebungsvariable ADMIN_PASSWORD"
    echo ""
    echo "Modulare Funktionen:"
    echo "- Multi-Drucker Setup: siehe data/printer_config.json"
    echo "- WiFi Access Point: siehe setup-wifi-ap.sh"
    echo ""
    echo "Bei Problemen:"
    echo "- Service neu starten: sudo systemctl restart bestellungssystem"
    echo "- Logs prüfen: sudo journalctl -u bestellungssystem -n 50"
    echo ""
else
    log_step "Installation mit Fehlern abgeschlossen"
    echo ""
    log_error "Bitte beheben Sie die oben aufgeführten Fehler und führen Sie das Skript erneut aus."
    echo ""
    exit 1
fi
