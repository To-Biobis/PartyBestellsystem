#!/bin/bash
# Test script for installation script logic
# This tests the install script without requiring root or making system changes

echo "======================================"
echo "Testing Installation Script Logic"
echo "======================================"
echo ""

ERRORS=0

# Test 1: Check script syntax
echo "[Test 1] Checking install-rpi.sh syntax..."
if bash -n install-rpi.sh; then
    echo "✓ install-rpi.sh syntax is valid"
else
    echo "✗ install-rpi.sh has syntax errors"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Check WiFi AP script syntax
echo "[Test 2] Checking setup-wifi-ap.sh syntax..."
if bash -n setup-wifi-ap.sh; then
    echo "✓ setup-wifi-ap.sh syntax is valid"
else
    echo "✗ setup-wifi-ap.sh has syntax errors"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: Check if scripts are executable
echo "[Test 3] Checking if scripts are executable..."
if [ -x install-rpi.sh ]; then
    echo "✓ install-rpi.sh is executable"
else
    echo "✗ install-rpi.sh is not executable"
    ERRORS=$((ERRORS + 1))
fi

if [ -x setup-wifi-ap.sh ]; then
    echo "✓ setup-wifi-ap.sh is executable"
else
    echo "✗ setup-wifi-ap.sh is not executable"
    ERRORS=$((ERRORS + 1))
fi

# Test 4: Check if required Python modules can be imported
echo "[Test 4] Testing Python module imports..."
if python3 -c "from src.printer import PrinterConfig, PrinterConfigManager, MultiPrinterManager, MultiPrinterQueueManager" 2>/dev/null; then
    echo "✓ All new printer modules can be imported"
else
    echo "✗ Failed to import new printer modules"
    ERRORS=$((ERRORS + 1))
fi

# Test 5: Check configuration file
echo "[Test 5] Checking configuration..."
if python3 -c "from src.config import Config; print('PRINTER_CONFIG_FILE:', Config.PRINTER_CONFIG_FILE)" | grep -q "printer_config.json"; then
    echo "✓ Configuration includes printer config file"
else
    echo "✗ Configuration missing printer config file"
    ERRORS=$((ERRORS + 1))
fi

# Test 6: Verify documentation files exist
echo "[Test 6] Checking documentation..."
if [ -f "MULTI_PRINTER_SETUP.md" ]; then
    echo "✓ MULTI_PRINTER_SETUP.md exists"
else
    echo "✗ MULTI_PRINTER_SETUP.md missing"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "WIFI_AP_SETUP.md" ]; then
    echo "✓ WIFI_AP_SETUP.md exists"
else
    echo "✗ WIFI_AP_SETUP.md missing"
    ERRORS=$((ERRORS + 1))
fi

# Test 7: Check README mentions new features
echo "[Test 7] Checking README for new features..."
if grep -q "Multi-Drucker" README.md; then
    echo "✓ README mentions Multi-Drucker"
else
    echo "✗ README doesn't mention Multi-Drucker"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "WiFi Access Point" README.md; then
    echo "✓ README mentions WiFi Access Point"
else
    echo "✗ README doesn't mention WiFi Access Point"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "======================================"
if [ $ERRORS -eq 0 ]; then
    echo "✓ All tests passed!"
    echo "======================================"
    exit 0
else
    echo "✗ $ERRORS test(s) failed"
    echo "======================================"
    exit 1
fi
