#!/bin/bash
# WiFi Access Point Setup for PartyBestellsystem
# Usage: sudo bash setup-wifi-ap.sh
#
# This script configures the Raspberry Pi as a WiFi Access Point
# so that ordering devices and printer Pis can connect to it

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

# Configuration variables - CHANGE THESE BEFORE RUNNING IN PRODUCTION!
SSID="${WIFI_SSID:-PartyBestellsystem}"
PASSWORD="${WIFI_PASSWORD:-party2024}"  # SECURITY WARNING: Change this default password!
CHANNEL="${WIFI_CHANNEL:-6}"
IP_ADDRESS="${AP_IP_ADDRESS:-192.168.4.1}"
DHCP_START="${DHCP_START:-192.168.4.2}"
DHCP_END="${DHCP_END:-192.168.4.20}"

# Password security check
if [ "$PASSWORD" = "party2024" ]; then
    log_warn "Using default password 'party2024' - INSECURE!"
    log_warn "Set WIFI_PASSWORD environment variable or edit script before production use"
    log_warn "Example: WIFI_PASSWORD='YourSecurePassword' sudo -E bash setup-wifi-ap.sh"
fi

# Password length check
if [ ${#PASSWORD} -lt 8 ]; then
    log_error "WiFi password must be at least 8 characters long"
    exit 1
fi

log_step "WiFi Access Point Setup"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Script muss als root ausgeführt werden (sudo bash setup-wifi-ap.sh)"
    exit 1
fi

# Check if WiFi interface exists
log_step "[1/8] Überprüfe WiFi-Interface"
if ! iw dev | grep -q "Interface wlan0"; then
    log_error "WiFi-Interface wlan0 nicht gefunden"
    log_error "Stellen Sie sicher, dass Ihr Raspberry Pi WiFi-Unterstützung hat"
    exit 1
else
    log_info "WiFi-Interface wlan0 gefunden"
fi

# Install required packages
log_step "[2/8] Installiere benötigte Pakete"
log_info "Installiere hostapd und dnsmasq..."
apt-get update
if ! apt-get install -y hostapd dnsmasq; then
    log_error "Fehler beim Installieren von hostapd und dnsmasq"
    exit 1
else
    log_info "Pakete installiert"
fi

# Stop services
log_info "Stoppe Services..."
systemctl stop hostapd
systemctl stop dnsmasq

# Configure static IP for wlan0
log_step "[3/8] Konfiguriere statische IP für wlan0"
log_info "Erstelle dhcpcd-Konfiguration..."

# Backup original dhcpcd.conf
if [ -f /etc/dhcpcd.conf ] && [ ! -f /etc/dhcpcd.conf.backup ]; then
    cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
    log_info "Backup von dhcpcd.conf erstellt"
fi

# Add static IP configuration
if ! grep -q "interface wlan0" /etc/dhcpcd.conf; then
    cat >> /etc/dhcpcd.conf << EOF

# Static IP configuration for Access Point
interface wlan0
    static ip_address=${IP_ADDRESS}/24
    nohook wpa_supplicant
EOF
    log_info "Statische IP konfiguriert: $IP_ADDRESS"
else
    log_info "Statische IP bereits konfiguriert"
fi

# Restart dhcpcd
log_info "Starte dhcpcd neu..."
systemctl restart dhcpcd

# Configure dnsmasq
log_step "[4/8] Konfiguriere DHCP-Server (dnsmasq)"

# Backup original dnsmasq.conf
if [ -f /etc/dnsmasq.conf ] && [ ! -f /etc/dnsmasq.conf.backup ]; then
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
    log_info "Backup von dnsmasq.conf erstellt"
fi

# Create dnsmasq configuration
cat > /etc/dnsmasq.conf << EOF
# PartyBestellsystem DHCP Configuration
interface=wlan0
dhcp-range=${DHCP_START},${DHCP_END},255.255.255.0,24h
domain=local
address=/partybestellung.local/${IP_ADDRESS}

# DNS server
server=8.8.8.8
server=8.8.4.4

# Logging
log-dhcp
log-queries
EOF

log_info "dnsmasq konfiguriert"

# Configure hostapd
log_step "[5/8] Konfiguriere Access Point (hostapd)"

# Create hostapd configuration
cat > /etc/hostapd/hostapd.conf << EOF
# PartyBestellsystem Access Point Configuration
interface=wlan0
driver=nl80211

# Network settings
ssid=${SSID}
hw_mode=g
channel=${CHANNEL}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0

# WPA2 security
wpa=2
wpa_passphrase=${PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

log_info "hostapd konfiguriert"
log_info "SSID: $SSID"
log_info "Passwort: $PASSWORD"

# Set hostapd to use our configuration
if ! grep -q "DAEMON_CONF=" /etc/default/hostapd; then
    echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd
else
    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
fi

# Enable IP forwarding
log_step "[6/8] Aktiviere IP-Forwarding"
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    log_info "IP-Forwarding aktiviert"
else
    log_info "IP-Forwarding bereits aktiviert"
fi

# Apply immediately
sysctl -w net.ipv4.ip_forward=1

# Configure NAT (if eth0 is available for internet sharing)
log_step "[7/8] Konfiguriere NAT für Internet-Sharing"
if ip link show eth0 &> /dev/null; then
    log_info "Ethernet-Interface gefunden, konfiguriere NAT..."
    
    # Clear existing rules
    iptables -t nat -F
    iptables -F
    
    # Add NAT rules
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
    
    # Save iptables rules
    sh -c "iptables-save > /etc/iptables.ipv4.nat"
    
    # Add restore command to rc.local
    if ! grep -q "iptables-restore" /etc/rc.local; then
        sed -i 's/exit 0//' /etc/rc.local
        echo "iptables-restore < /etc/iptables.ipv4.nat" >> /etc/rc.local
        echo "exit 0" >> /etc/rc.local
        log_info "iptables werden beim Boot wiederhergestellt"
    fi
    
    log_info "NAT konfiguriert (Internet-Sharing über eth0)"
else
    log_warn "Kein Ethernet-Interface gefunden - Internet-Sharing nicht verfügbar"
    log_warn "Access Point funktioniert trotzdem für lokale Verbindungen"
fi

# Enable and start services
log_step "[8/8] Aktiviere und starte Services"

log_info "Unmask hostapd..."
systemctl unmask hostapd

log_info "Aktiviere hostapd..."
systemctl enable hostapd

log_info "Aktiviere dnsmasq..."
systemctl enable dnsmasq

log_info "Starte hostapd..."
if ! systemctl start hostapd; then
    log_error "Fehler beim Starten von hostapd"
    log_error "Logs: journalctl -u hostapd -n 20"
else
    log_info "hostapd gestartet"
fi

log_info "Starte dnsmasq..."
if ! systemctl start dnsmasq; then
    log_error "Fehler beim Starten von dnsmasq"
    log_error "Logs: journalctl -u dnsmasq -n 20"
else
    log_info "dnsmasq gestartet"
fi

# Verify services
sleep 2
log_info "Überprüfe Service-Status..."
if ! systemctl is-active --quiet hostapd; then
    log_error "hostapd läuft nicht"
    ERRORS+=("hostapd service not running")
else
    log_info "hostapd läuft"
fi

if ! systemctl is-active --quiet dnsmasq; then
    log_error "dnsmasq läuft nicht"
    ERRORS+=("dnsmasq service not running")
else
    log_info "dnsmasq läuft"
fi

# Summary
echo ""
log_step "Setup abgeschlossen!"

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Warnings:${NC}"
    for warning in "${WARNINGS[@]}"; do
        echo "  - $warning"
    done
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Errors:${NC}"
    for error in "${ERRORS[@]}"; do
        echo "  - $error"
    done
    echo ""
    echo "Bitte beheben Sie die Fehler und prüfen Sie die Logs."
    exit 1
else
    echo ""
    log_info "Access Point erfolgreich eingerichtet!"
    echo ""
    echo "Netzwerk-Informationen:"
    echo "  SSID: $SSID"
    echo "  Passwort: $PASSWORD"
    echo "  IP-Adresse: $IP_ADDRESS"
    echo "  DHCP-Bereich: $DHCP_START - $DHCP_END"
    echo ""
    echo "Verbinden Sie Ihre Geräte mit dem WiFi-Netzwerk '$SSID'"
    echo "und öffnen Sie im Browser: http://$IP_ADDRESS"
    echo "oder: http://partybestellung.local"
    echo ""
    echo "Status überprüfen:"
    echo "  sudo systemctl status hostapd"
    echo "  sudo systemctl status dnsmasq"
    echo ""
    echo "Logs anzeigen:"
    echo "  sudo journalctl -u hostapd -f"
    echo "  sudo journalctl -u dnsmasq -f"
    echo ""
fi
