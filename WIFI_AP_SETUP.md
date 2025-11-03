# WiFi Access Point Setup Guide

This guide explains how to configure your Raspberry Pi as a WiFi Access Point for the PartyBestellsystem, allowing ordering devices and printer Pis to connect directly to it.

## Overview

Setting up the Raspberry Pi as a WiFi Access Point (AP) allows you to create a standalone network for your ordering system without needing an existing WiFi infrastructure. This is perfect for:

- Events and parties without WiFi
- Mobile catering operations
- Temporary setups
- Isolated networks for security
- Multi-location setups with multiple Raspberry Pis

## Prerequisites

- Raspberry Pi with built-in WiFi (Raspberry Pi 3, 4, or Zero W)
- Ethernet connection (optional, for internet sharing)
- Root/sudo access
- PartyBestellsystem already installed

## Quick Setup

### One-Command Installation

```bash
cd PartyBestellsystem
sudo bash setup-wifi-ap.sh
```

The script will:
1. Check for WiFi hardware
2. Install required packages (hostapd, dnsmasq)
3. Configure static IP for WiFi interface
4. Setup DHCP server
5. Configure Access Point settings
6. Enable IP forwarding (for internet sharing)
7. Setup NAT if ethernet is available
8. Start all services

### Default Configuration

After running the script, the following settings will be active:

- **SSID**: `PartyBestellsystem`
- **Password**: `party2024` ⚠️ **CHANGE THIS IN PRODUCTION!**
- **IP Address**: `192.168.4.1`
- **DHCP Range**: `192.168.4.2` - `192.168.4.20`
- **DNS**: Google DNS (8.8.8.8, 8.8.4.4)

**SECURITY WARNING**: The default password is weak and publicly visible. Change it before production use!

## Customizing the Configuration

### Changing Network Settings

**Recommended Method: Using Environment Variables**

```bash
# Set custom configuration via environment variables
WIFI_SSID="MyCustomSSID" \
WIFI_PASSWORD="MyVerySecurePassword123!" \
WIFI_CHANNEL=11 \
AP_IP_ADDRESS="192.168.10.1" \
sudo -E bash setup-wifi-ap.sh
```

**Alternative: Edit Script Directly**

Before running the setup script, edit it to change default values:

```bash
nano setup-wifi-ap.sh
```

Find and modify these variables:

```bash
SSID="${WIFI_SSID:-PartyBestellsystem}"      # Change to your desired network name
PASSWORD="${WIFI_PASSWORD:-party2024}"        # Change to your desired password (min 8 chars) - CHANGE THIS!
CHANNEL="${WIFI_CHANNEL:-6}"                  # WiFi channel (1-11)
IP_ADDRESS="${AP_IP_ADDRESS:-192.168.4.1}"   # Router IP address
DHCP_START="${DHCP_START:-192.168.4.2}"      # Start of DHCP range
DHCP_END="${DHCP_END:-192.168.4.20}"         # End of DHCP range
```

### Manual Configuration

If you prefer manual configuration or need to troubleshoot, follow these steps:

#### 1. Install Required Packages

```bash
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq
```

#### 2. Configure Static IP

Edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:

```conf
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

#### 3. Configure DHCP Server

Edit `/etc/dnsmasq.conf`:

```bash
sudo nano /etc/dnsmasq.conf
```

Add:

```conf
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/partybestellung.local/192.168.4.1
```

#### 4. Configure Access Point

Create `/etc/hostapd/hostapd.conf`:

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Add:

```conf
interface=wlan0
driver=nl80211
ssid=PartyBestellsystem
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=party2024
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

#### 5. Enable Services

```bash
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl start hostapd
sudo systemctl start dnsmasq
```

## Internet Sharing

If you connect your Raspberry Pi to the internet via Ethernet (eth0), the WiFi clients will automatically have internet access through NAT.

### Enable IP Forwarding

Edit `/etc/sysctl.conf`:

```bash
sudo nano /etc/sysctl.conf
```

Uncomment or add:

```conf
net.ipv4.ip_forward=1
```

Apply immediately:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

### Configure NAT

```bash
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
```

Save the rules:

```bash
sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
```

Make them persistent by editing `/etc/rc.local`:

```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:

```bash
iptables-restore < /etc/iptables.ipv4.nat
```

## Connecting Devices

### Ordering Tablets/Phones

1. Open WiFi settings on the device
2. Look for network: `PartyBestellsystem` (or your custom SSID)
3. Enter password: `party2024` (or your custom password)
4. Once connected, open browser
5. Navigate to: `http://192.168.4.1` or `http://partybestellung.local`

### Additional Printer Pis

To connect additional Raspberry Pis with printers to the main Pi's network:

1. On the printer Pi, open WiFi settings
2. Connect to the `PartyBestellsystem` network
3. Configure the printer Pi to communicate with the main Pi's IP (192.168.4.1)

## Network Topology Examples

### Example 1: Simple Setup

```
[Main Raspberry Pi]
    |
    +--- WiFi AP (192.168.4.1)
           |
           +--- Tablet 1 (192.168.4.2)
           +--- Tablet 2 (192.168.4.3)
           +--- Phone 1 (192.168.4.4)
```

### Example 2: With Internet Sharing

```
[Internet] --- [Ethernet] --- [Main Raspberry Pi]
                                     |
                                     +--- WiFi AP (192.168.4.1)
                                            |
                                            +--- Ordering devices
```

### Example 3: Multi-Printer Setup

```
[Main Raspberry Pi + Printer]
    |
    +--- WiFi AP (192.168.4.1)
           |
           +--- Printer Pi 1 (Kitchen) (192.168.4.5)
           +--- Printer Pi 2 (Bar) (192.168.4.6)
           +--- Tablet 1 (192.168.4.2)
           +--- Tablet 2 (192.168.4.3)
```

## Monitoring and Management

### Check Access Point Status

```bash
# Check hostapd status
sudo systemctl status hostapd

# Check dnsmasq status
sudo systemctl status dnsmasq

# View connected devices
sudo iw dev wlan0 station dump
```

### View DHCP Leases

```bash
# Current DHCP leases
cat /var/lib/misc/dnsmasq.leases

# Or monitor in real-time
tail -f /var/log/syslog | grep dnsmasq
```

### Check WiFi Interface

```bash
# Interface status
ip addr show wlan0

# WiFi interface details
iw dev wlan0 info
```

### View Logs

```bash
# hostapd logs
sudo journalctl -u hostapd -f

# dnsmasq logs
sudo journalctl -u dnsmasq -f

# System logs related to WiFi
sudo tail -f /var/log/syslog | grep -E "hostapd|dnsmasq"
```

## Troubleshooting

### Access Point Not Visible

**Problem**: WiFi network doesn't appear in available networks.

**Solutions**:
1. Check if hostapd is running: `sudo systemctl status hostapd`
2. View hostapd logs: `sudo journalctl -u hostapd -n 50`
3. Check WiFi interface: `iw dev`
4. Verify hostapd configuration: `sudo hostapd -d /etc/hostapd/hostapd.conf`
5. Try a different channel: Edit `/etc/hostapd/hostapd.conf` and change `channel=6` to `channel=1` or `channel=11`

### Can't Connect to Network

**Problem**: Network is visible but devices can't connect.

**Solutions**:
1. Verify password is correct (minimum 8 characters)
2. Check hostapd logs for authentication errors
3. Try forgetting the network on the device and reconnecting
4. Check if WPA2 is supported by the client device
5. Temporarily disable WPA to test: Set `wpa=0` in hostapd.conf

### Connected but No Access to Web Interface

**Problem**: Devices connect to WiFi but can't access the website.

**Solutions**:
1. Check Pi's IP address: `ip addr show wlan0`
2. Verify static IP is set: `cat /etc/dhcpcd.conf | grep wlan0 -A 2`
3. Check if web server is running: `sudo systemctl status bestellungssystem`
4. Test from Pi itself: `curl http://localhost:5000`
5. Check nginx: `sudo systemctl status nginx`
6. Verify firewall isn't blocking: `sudo iptables -L`

### No Internet Access for Clients

**Problem**: WiFi works but clients have no internet (when ethernet is connected).

**Solutions**:
1. Check IP forwarding: `cat /proc/sys/net/ipv4/ip_forward` (should be 1)
2. Check iptables rules: `sudo iptables -t nat -L -v`
3. Verify ethernet connection: `ip addr show eth0`
4. Check if Pi has internet: `ping 8.8.8.8`
5. Reconfigure NAT rules (see Internet Sharing section)

### Service Won't Start

**Problem**: hostapd or dnsmasq fails to start.

**Solutions**:
1. Check for configuration errors:
   ```bash
   sudo hostapd -d /etc/hostapd/hostapd.conf
   sudo dnsmasq --test
   ```
2. Verify no other service is using the ports
3. Check if another program is controlling wlan0
4. Restart services in correct order:
   ```bash
   sudo systemctl stop hostapd
   sudo systemctl stop dnsmasq
   sudo systemctl stop dhcpcd
   sudo systemctl start dhcpcd
   sudo systemctl start dnsmasq
   sudo systemctl start hostapd
   ```

## Advanced Configuration

### Increase DHCP Range

To support more devices, edit `/etc/dnsmasq.conf`:

```conf
dhcp-range=192.168.4.2,192.168.4.100,255.255.255.0,24h
```

### Static IP for Specific Devices

In `/etc/dnsmasq.conf`, add:

```conf
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.4.50,tablet1
```

Where `aa:bb:cc:dd:ee:ff` is the device's MAC address.

### Hidden Network

To hide the SSID, edit `/etc/hostapd/hostapd.conf`:

```conf
ignore_broadcast_ssid=1
```

Note: Devices will need to manually enter the network name.

### 5GHz WiFi

If your Raspberry Pi supports 5GHz (Pi 3B+ and newer):

Edit `/etc/hostapd/hostapd.conf`:

```conf
hw_mode=a
channel=36
```

Valid 5GHz channels: 36, 40, 44, 48

### Guest Network Isolation

To prevent devices from communicating with each other:

```bash
sudo iptables -I FORWARD -i wlan0 -o wlan0 -j DROP
```

## Security Best Practices

1. **Change Default Password**: Always use a strong password (minimum 12 characters)
2. **Use WPA3**: If supported, upgrade to WPA3 for better security
3. **Disable WPS**: WPS is not configured by default; keep it that way
4. **Regular Updates**: Keep system and packages updated
5. **Monitor Connections**: Regularly check connected devices
6. **Limit DHCP Range**: Only allow as many connections as you need
7. **Use MAC Filtering**: For fixed installations, configure MAC address whitelist

## Reverting Changes

To revert the Access Point setup and restore normal WiFi client mode:

```bash
# Stop and disable services
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq

# Restore dhcpcd.conf
sudo cp /etc/dhcpcd.conf.backup /etc/dhcpcd.conf

# Restart networking
sudo systemctl restart dhcpcd
sudo systemctl restart networking
```

## Support

For issues or questions:
1. Check the logs: `sudo journalctl -u hostapd -f` and `sudo journalctl -u dnsmasq -f`
2. Verify your Raspberry Pi model supports WiFi AP mode
3. Test with a different device to isolate client-side issues
4. Create a GitHub issue with your configuration and error messages
