#!/usr/bin/env python3
"""Test script for modular components"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all module imports"""
    print("Testing module imports...")
    
    try:
        from src.config import Config
        print("✓ Config module imported")
        
        from src.database import DataStorage
        print("✓ DataStorage module imported")
        
        from src.utils import ThreadSafeDict, setup_logging
        print("✓ Utils modules imported")
        
        from src.orders import OrderManager, OrderFormatter
        print("✓ Order modules imported")
        
        from src.printer import PrinterManager, PrintQueueManager
        print("✓ Printer modules imported (note: actual printer not required for import)")
        
        print("\n✓ All module imports successful!")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    
    try:
        from src.config import Config
        
        assert hasattr(Config, 'DATA_DIR'), "DATA_DIR not found"
        assert hasattr(Config, 'PRINTER_VENDOR_ID'), "PRINTER_VENDOR_ID not found"
        assert hasattr(Config, 'SECRET_KEY'), "SECRET_KEY not found"
        
        print(f"  Data directory: {Config.DATA_DIR}")
        print(f"  Base directory: {Config.BASE_DIR}")
        
        print("✓ Configuration test passed")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {str(e)}")
        return False

def test_data_storage():
    """Test data storage module"""
    print("\nTesting data storage...")
    
    try:
        from src.database import DataStorage
        from src.config import Config
        
        # Create test storage
        storage = DataStorage(
            Config.DATA_DIR,
            Config.BACKUP_DIR,
            max_backups=5
        )
        
        # Test data operations
        test_file = os.path.join(Config.DATA_DIR, 'test_data.json')
        test_data = [{'id': 1, 'name': 'Test'}]
        
        # Test save
        success = storage.save_data(test_file, test_data)
        assert success, "Save failed"
        
        # Test load
        loaded_data = storage.load_data(test_file, [])
        assert loaded_data == test_data, "Loaded data doesn't match"
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("✓ Data storage test passed")
        return True
    except Exception as e:
        print(f"✗ Data storage test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_order_manager():
    """Test order manager"""
    print("\nTesting order manager...")
    
    try:
        from src.orders import OrderManager
        from src.database import DataStorage
        from src.config import Config
        
        storage = DataStorage(Config.DATA_DIR, Config.BACKUP_DIR)
        
        # Create test data
        test_products = os.path.join(Config.DATA_DIR, 'test_products.json')
        test_categories = os.path.join(Config.DATA_DIR, 'test_categories.json')
        test_orders = os.path.join(Config.DATA_DIR, 'test_orders.json')
        
        storage.save_data(test_products, [
            {'id': 1, 'name': 'Test Product', 'kategorie': 1, 'price': 5.99}
        ])
        storage.save_data(test_categories, [
            {'id': 1, 'name': 'Test Category'}
        ])
        storage.save_data(test_orders, [])
        
        # Create order manager
        manager = OrderManager(
            storage,
            test_products,
            test_categories,
            test_orders
        )
        
        # Test create order
        order = manager.create_order('1', 1, 2, 'Test comment')
        assert order is not None, "Order creation failed"
        assert order['menge'] == 2, "Order quantity wrong"
        
        # Test save
        success = manager.save_orders()
        assert success, "Save orders failed"
        
        # Cleanup
        for f in [test_products, test_categories, test_orders]:
            if os.path.exists(f):
                os.remove(f)
        
        print("✓ Order manager test passed")
        return True
    except Exception as e:
        print(f"✗ Order manager test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_order_formatter():
    """Test order formatter"""
    print("\nTesting order formatter...")
    
    try:
        from src.orders import OrderFormatter
        from datetime import datetime
        
        formatter = OrderFormatter(paper_width=32)
        
        # Create test order
        test_orders = [{
            'id': 1,
            'menge': 2,
            'produkt': 'Test Product',
            'price': 5.99,
            'kommentar': 'Test comment',
            'zeitpunkt': datetime.now().isoformat()
        }]
        
        # Test formatting
        content = formatter.format_orders_for_category('1', 'Test Category', test_orders)
        
        assert 'Tisch 1' in content, "Table not in content"
        assert 'Test Product' in content, "Product not in content"
        assert 'Test Category' in content, "Category not in content"
        
        print("✓ Order formatter test passed")
        return True
    except Exception as e:
        print(f"✗ Order formatter test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("PartyBestellsystem Module Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_data_storage,
        test_order_manager,
        test_order_formatter
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 50)
    
    return all(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
