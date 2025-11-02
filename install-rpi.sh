#!/bin/bash
# Installation script for PartyBestellsystem on Raspberry Pi
# Usage: sudo bash install-rpi.sh

set -e  # Exit on error

echo "======================================"
echo "PartyBestellsystem Installation"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Bitte als root ausführen (sudo bash install-rpi.sh)"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="/home/$ACTUAL_USER/PartyBestellsystem"

echo "Installation wird durchgeführt für Benutzer: $ACTUAL_USER"
echo "Installationsverzeichnis: $INSTALL_DIR"
echo ""

# Update system
echo "[1/10] System wird aktualisiert..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "[2/10] Installiere System-Abhängigkeiten..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    libusb-1.0-0-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev

# Create installation directory
echo "[3/10] Erstelle Installationsverzeichnis..."
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
fi

# Copy or clone repository
echo "[4/10] Kopiere Anwendungsdateien..."
if [ -d "/tmp/PartyBestellsystem" ]; then
    cp -r /tmp/PartyBestellsystem/* "$INSTALL_DIR/"
elif [ "$(basename $(pwd))" = "PartyBestellsystem" ]; then
    cp -r ./* "$INSTALL_DIR/"
else
    echo "Hinweis: Bitte führen Sie dieses Skript aus dem PartyBestellsystem-Verzeichnis aus"
    echo "oder klonen Sie das Repository nach /tmp/PartyBestellsystem"
    exit 1
fi

# Set ownership
chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR"

# Create Python virtual environment
echo "[5/10] Erstelle Python Virtual Environment..."
cd "$INSTALL_DIR"
sudo -u $ACTUAL_USER python3 -m venv .venv

# Install Python dependencies
echo "[6/10] Installiere Python-Abhängigkeiten..."
sudo -u $ACTUAL_USER .venv/bin/pip install --upgrade pip
sudo -u $ACTUAL_USER .venv/bin/pip install -r requirements.txt

# Create data directories
echo "[7/10] Erstelle Datenverzeichnisse..."
sudo -u $ACTUAL_USER mkdir -p "$INSTALL_DIR/data"
sudo -u $ACTUAL_USER mkdir -p "$INSTALL_DIR/data/backups"

# Initialize data files if they don't exist
if [ ! -f "$INSTALL_DIR/data/categories.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/categories.json"
fi
if [ ! -f "$INSTALL_DIR/data/products.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/products.json"
fi
if [ ! -f "$INSTALL_DIR/data/orders.json" ]; then
    echo '[]' > "$INSTALL_DIR/data/orders.json"
fi

chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR/data"

# Setup USB permissions for printer
echo "[8/10] Konfiguriere USB-Berechtigungen für Drucker..."
usermod -a -G lp $ACTUAL_USER

# Create systemd service file
echo "[9/10] Erstelle systemd Service..."
cat > /etc/systemd/system/bestellungssystem.service << EOF
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

# Configure nginx
echo "[10/10] Konfiguriere nginx..."
cat > /etc/nginx/sites-available/bestellungssystem << EOF
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

# Enable nginx site
ln -sf /etc/nginx/sites-available/bestellungssystem /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Reload systemd and enable services
systemctl daemon-reload
systemctl enable bestellungssystem
systemctl enable nginx

# Start services
systemctl restart nginx
systemctl restart bestellungssystem

echo ""
echo "======================================"
echo "Installation abgeschlossen!"
echo "======================================"
echo ""
echo "Die Anwendung wurde erfolgreich installiert und gestartet."
echo ""
echo "Nächste Schritte:"
echo "1. Überprüfen Sie den Status: sudo systemctl status bestellungssystem"
echo "2. Logs ansehen: sudo journalctl -u bestellungssystem -f"
echo "3. Öffnen Sie einen Browser und navigieren Sie zu http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Standard-Admin-Passwort: admin123"
echo "WICHTIG: Ändern Sie das Passwort über die Umgebungsvariable ADMIN_PASSWORD"
echo ""
echo "Bei Problemen:"
echo "- Service neu starten: sudo systemctl restart bestellungssystem"
echo "- Logs prüfen: sudo journalctl -u bestellungssystem -n 50"
echo ""
