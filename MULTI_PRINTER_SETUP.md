# Multi-Printer Setup Guide

This guide explains how to configure and use multiple printers with category-based routing in the PartyBestellsystem.

## Overview

The modular printer system allows you to:
- Configure multiple printers (e.g., one for kitchen, one for bar)
- Route different categories to different printers automatically
- Manage printer configurations dynamically
- Test and monitor individual printers

## Configuration

### Printer Configuration File

The printer configuration is stored in `data/printer_config.json`. This file is created automatically during installation.

### Basic Structure

```json
{
  "printers": [
    {
      "printer_id": "kitchen",
      "name": "Kitchen Printer",
      "vendor_id": 4776,
      "product_id": 3605,
      "categories": ["Essen", "Desserts"],
      "enabled": true
    },
    {
      "printer_id": "bar",
      "name": "Bar Printer",
      "vendor_id": 4776,
      "product_id": 3605,
      "categories": ["Getränke"],
      "enabled": true
    },
    {
      "printer_id": "default",
      "name": "Default Printer",
      "vendor_id": 4776,
      "product_id": 3605,
      "categories": [],
      "enabled": true
    }
  ]
}
```

### Configuration Fields

- **printer_id**: Unique identifier for the printer (string)
- **name**: Human-readable name for the printer (string)
- **vendor_id**: USB Vendor ID in decimal format (integer)
- **product_id**: USB Product ID in decimal format (integer)
- **categories**: List of category names this printer handles (array of strings)
- **enabled**: Whether the printer is active (boolean)

### Finding USB IDs

To find your printer's USB IDs, run:

```bash
lsusb
```

Example output:
```
Bus 001 Device 004: ID 04b8:0e15 Seiko Epson Corp. TM-T20II
```

In this example:
- Vendor ID: `04b8` (hex) = `1208` (decimal)
- Product ID: `0e15` (hex) = `3605` (decimal)

Convert hex to decimal if needed:
```bash
echo $((0x04b8))  # Returns: 1208
echo $((0x0e15))  # Returns: 3605
```

## Category Routing

### How It Works

1. When an order is placed, the system checks which category the items belong to
2. It looks up which printer is configured for that category
3. The order is sent to the appropriate printer's queue
4. If no specific printer is configured, it uses the default printer

### Empty Categories Array

A printer with an empty `categories` array acts as a fallback/default printer and will handle all categories not assigned to other printers.

### Multiple Printers for Same Category

If multiple printers are configured for the same category, the first enabled printer in the configuration will be used.

## Setup Examples

### Example 1: Kitchen and Bar Split

Perfect for restaurants with separate kitchen and bar areas:

```json
{
  "printers": [
    {
      "printer_id": "kitchen",
      "name": "Kitchen Printer",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Vorspeisen", "Hauptgerichte", "Beilagen"],
      "enabled": true
    },
    {
      "printer_id": "bar",
      "name": "Bar Printer",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Getränke", "Cocktails"],
      "enabled": true
    }
  ]
}
```

### Example 2: Multiple Locations

For events with multiple service points:

```json
{
  "printers": [
    {
      "printer_id": "station1",
      "name": "Station 1 - Food",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Essen"],
      "enabled": true
    },
    {
      "printer_id": "station2",
      "name": "Station 2 - Drinks",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Getränke"],
      "enabled": true
    },
    {
      "printer_id": "station3",
      "name": "Station 3 - Desserts",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": ["Desserts", "Kaffee"],
      "enabled": true
    }
  ]
}
```

### Example 3: Backup Printer

With a backup printer for when the main one is offline:

```json
{
  "printers": [
    {
      "printer_id": "main",
      "name": "Main Printer",
      "vendor_id": 1208,
      "product_id": 3605,
      "categories": [],
      "enabled": true
    },
    {
      "printer_id": "backup",
      "name": "Backup Printer",
      "vendor_id": 1208,
      "product_id": 3606,
      "categories": [],
      "enabled": false
    }
  ]
}
```

To switch to backup, set `main.enabled = false` and `backup.enabled = true`.

## Testing Printers

### Test Individual Printer

After configuring a printer, you can test it:

```bash
# Via command line (requires app running)
curl -X POST http://localhost:5000/admin/test-printer/kitchen
```

### Test All Printers

```bash
curl -X POST http://localhost:5000/admin/test-all-printers
```

### Manual Testing

Connect to the printer and send a test print:

```python
from src.printer import PrinterConfigManager, MultiPrinterManager

# Load configuration
config_manager = PrinterConfigManager('data/printer_config.json')
multi_manager = MultiPrinterManager(config_manager)

# Test specific printer
result = multi_manager.test_printer('kitchen')
print(f"Kitchen printer test: {'Success' if result else 'Failed'}")

# Test all printers
results = multi_manager.test_all_printers()
for printer_id, success in results.items():
    print(f"{printer_id}: {'Success' if success else 'Failed'}")
```

## Troubleshooting

### Printer Not Found

**Problem**: Printer shows as not initialized or not found.

**Solutions**:
1. Check USB connection: `lsusb`
2. Verify USB IDs in configuration match actual printer
3. Check printer permissions: `groups` should include `lp`
4. Restart the service: `sudo systemctl restart bestellungssystem`

### Orders Going to Wrong Printer

**Problem**: Orders are printed on the wrong printer.

**Solutions**:
1. Check category names match exactly (case-sensitive)
2. Verify printer configuration in `data/printer_config.json`
3. Check that only one printer is assigned to each category
4. Reload configuration or restart service

### Printer Queue Stuck

**Problem**: Print jobs are queuing but not printing.

**Solutions**:
1. Check printer status in admin panel
2. View logs: `sudo journalctl -u bestellungssystem -f`
3. Test printer connection manually
4. Restart the service to reset queues

### Configuration Not Loading

**Problem**: Changes to `printer_config.json` are not reflected.

**Solutions**:
1. Verify JSON syntax is valid (use a JSON validator)
2. Check file permissions: `ls -la data/printer_config.json`
3. Restart the service: `sudo systemctl restart bestellungssystem`
4. Check logs for configuration errors

## Advanced Usage

### Dynamic Configuration Updates

The system can reload printer configuration without restart:

```python
from src.printer import PrinterConfigManager, MultiPrinterQueueManager

# Reload configuration
queue_manager.reload_configuration()
```

### Custom Printer Classes

You can extend the system with custom printer managers:

```python
from src.printer import PrinterManager

class CustomPrinterManager(PrinterManager):
    def __init__(self, vendor_id, product_id):
        super().__init__(vendor_id, product_id)
        # Add custom initialization
    
    def custom_print_format(self, content):
        # Add custom formatting
        pass
```

### Monitoring Print Status

Get status of all printer queues:

```python
from src.printer import MultiPrinterQueueManager

status = queue_manager.get_queue_status()
for printer_id, info in status.items():
    print(f"{printer_id}:")
    print(f"  Queue size: {info['queue_size']}")
    print(f"  Is empty: {info['is_empty']}")
    print(f"  Worker active: {info['worker_active']}")
```

## Best Practices

1. **Always Test**: Test each printer configuration before going live
2. **Use Descriptive Names**: Use clear printer names and IDs
3. **Plan Categories**: Plan your category-to-printer mapping carefully
4. **Keep Backups**: Keep a backup of your working configuration
5. **Monitor Queues**: Regularly check queue status during busy periods
6. **Update Incrementally**: Make configuration changes incrementally and test

## Support

For issues or questions:
1. Check the logs: `sudo journalctl -u bestellungssystem -f`
2. Verify USB connections and permissions
3. Test individual printers separately
4. Create a GitHub issue with your configuration and error messages
