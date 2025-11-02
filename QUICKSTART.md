# Quick Start Guide

Get PartyBestellsystem up and running in 5 minutes!

## 🚀 For Raspberry Pi (Recommended)

### One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/To-Biobis/PartyBestellsystem/main/install-rpi.sh | sudo bash
```

Or download and run:

```bash
git clone https://github.com/To-Biobis/PartyBestellsystem.git
cd PartyBestellsystem
sudo bash install-rpi.sh
```

The script will:
- ✓ Install all dependencies
- ✓ Setup Python environment
- ✓ Configure system service
- ✓ Setup Nginx reverse proxy
- ✓ Start the application automatically

**Done!** Open your browser: `http://your-raspberry-pi-ip`

---

## 💻 For Development / Testing

### Prerequisites
- Python 3.7+
- pip
- git

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/To-Biobis/PartyBestellsystem.git
cd PartyBestellsystem

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python3 run.py
```

**Done!** Open your browser: `http://localhost:5000`

---

## 🎯 First Steps After Installation

### 1. Change Admin Password

**Important!** Change the default password immediately:

```bash
# On Raspberry Pi
sudo systemctl stop bestellungssystem
export ADMIN_PASSWORD="YourSecurePassword"
sudo systemctl start bestellungssystem

# Or add to service file permanently:
sudo nano /etc/systemd/system/bestellungssystem.service
# Add: Environment="ADMIN_PASSWORD=YourSecurePassword"
sudo systemctl daemon-reload
sudo systemctl restart bestellungssystem
```

### 2. Setup Printer

Connect your ESC/POS thermal printer via USB.

**Check printer connection:**
```bash
lsusb
# Look for your printer (e.g., Epson TM-T20II: 04b8:0e15)
```

**If different printer, update config:**
```bash
nano src/config/settings.py
# Update PRINTER_VENDOR_ID and PRINTER_PRODUCT_ID
```

### 3. Add Categories and Products

1. Go to `http://your-ip/admin/login`
2. Login (default password: `admin123`)
3. Add categories (e.g., "Getränke", "Essen", "Desserts")
4. Add products with prices

### 4. Test Order Flow

1. Open `http://your-ip` in browser
2. Enter table number (e.g., "1")
3. Select products
4. Click "Bestellen"
5. **Order prints immediately!** ⚡

---

## 📊 Monitoring & Management

### Check System Status

```bash
# Service status
sudo systemctl status bestellungssystem

# View logs (live)
sudo journalctl -u bestellungssystem -f

# View last 50 log entries
sudo journalctl -u bestellungssystem -n 50
```

### Service Control

```bash
# Start service
sudo systemctl start bestellungssystem

# Stop service
sudo systemctl stop bestellungssystem

# Restart service
sudo systemctl restart bestellungssystem

# Enable auto-start on boot
sudo systemctl enable bestellungssystem
```

### Access Points

- **Customer Interface**: `http://your-ip`
- **Admin Panel**: `http://your-ip/admin/login`
- **Status Check**: Check logs or admin panel

---

## 🔧 Configuration

### Environment Variables

Set in `/etc/systemd/system/bestellungssystem.service`:

```ini
[Service]
Environment="SECRET_KEY=your-secret-key-here"
Environment="ADMIN_PASSWORD=your-secure-password"
Environment="FLASK_ENV=production"
```

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart bestellungssystem
```

### Data Files

Location: `/home/pi/PartyBestellsystem/data/`

- `categories.json` - Product categories
- `products.json` - Products with prices
- `orders.json` - Current orders
- `backups/` - Automatic hourly backups

### Manual Backup

```bash
cp -r data data_backup_$(date +%Y%m%d_%H%M%S)
```

---

## 🎨 Using the System

### Customer Flow

1. **Select Table**
   - Enter table number (1-999)
   - Click "Bestellen"

2. **Add Items**
   - Click products to add to cart
   - Long-press to add comment
   - See cart badge (🛒) with item count

3. **Place Order**
   - Click cart button
   - Review items
   - Click "Bestellen"
   - **Order prints immediately!**

4. **Track Status**
   - ⏳ **New/Waiting** - Just placed, will print soon
   - 🖨️ **Printing** - Currently being printed
   - ✓ **Printed** - Successfully printed

### Admin Tasks

1. **Login**: `/admin/login` (default: admin123)

2. **Add Category**
   - Go to admin panel
   - Enter category name
   - Click "Kategorie hinzufügen"

3. **Add Product**
   - Select category
   - Enter product name and price
   - Click "Produkt hinzufügen"

4. **Manage Orders**
   - View all orders
   - Delete individual orders
   - Clean up completed orders

5. **Update Prices**
   - Enter new price
   - Click "Preis aktualisieren"

---

## 🚨 Troubleshooting

### Printer Not Printing

```bash
# Check USB connection
lsusb

# Check logs
sudo journalctl -u bestellungssystem -n 50 | grep -i printer

# Check permissions
groups
# Should show "lp" group

# Add user to lp group if missing
sudo usermod -a -G lp pi
# Logout and login again
```

### Port 5000 Already in Use

```bash
# Find process
sudo netstat -tulpn | grep 5000

# Kill old process
sudo kill -9 <PID>

# Or change port in src/config/settings.py
```

### Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u bestellungssystem -n 100 --no-pager

# Check Python path
cd /home/pi/PartyBestellsystem
source .venv/bin/activate
python3 run.py
# Look for error messages

# Check dependencies
pip install -r requirements.txt
```

### Web Page Not Loading

```bash
# Check if service is running
sudo systemctl status bestellungssystem

# Check nginx
sudo systemctl status nginx

# Restart both
sudo systemctl restart bestellungssystem
sudo systemctl restart nginx

# Check from Raspberry Pi itself
curl http://localhost:5000
```

---

## 📱 Mobile Access

The interface is mobile-friendly! Just open the URL on any device:

- **Tablets**: Perfect for customers to place orders
- **Phones**: Works great for quick orders
- **Desktop**: Full functionality

**Network Requirements:**
- All devices on same network as Raspberry Pi
- Or setup port forwarding for external access

---

## 🎓 Next Steps

- ✅ Change default admin password
- ✅ Setup your categories and products
- ✅ Test the complete order flow
- ✅ Train staff on admin interface
- 📚 Read full documentation:
  - [README.md](README.md) - Complete user guide
  - [DEVELOPMENT.md](DEVELOPMENT.md) - For developers
  - [MIGRATION.md](MIGRATION.md) - Upgrading from v1.x

---

## 🆘 Getting Help

1. **Check Logs First**:
   ```bash
   sudo journalctl -u bestellungssystem -n 50
   ```

2. **Review Documentation**:
   - README.md for general usage
   - TROUBLESHOOTING section above
   - DEVELOPMENT.md for technical details

3. **Create GitHub Issue**:
   - Include error messages
   - Include relevant logs
   - Describe what you tried
   - Mention your Raspberry Pi and Python versions

---

## ⭐ Features at a Glance

✅ **Instant Printing** - No delays, prints immediately  
✅ **Real-time Status** - See order status live  
✅ **Mobile Friendly** - Works on any device  
✅ **Reliable** - Atomic saves, automatic backups  
✅ **Easy Setup** - One-line installation  
✅ **Admin Panel** - Manage categories, products, orders  
✅ **Multi-Category** - Organize by food, drinks, etc.  
✅ **Comments** - Add notes to orders  
✅ **Auto-Backup** - Hourly backups, never lose data  

---

**Ready to go!** Start taking orders now! 🎉
