"""Thread-safe data structures"""

import threading


class ThreadSafeDict:
    """Thread-safe dictionary wrapper"""
    
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

    def delete(self, key):
        with self._lock:
            if key in self._data:
                del self._data[key]

    def items(self):
        with self._lock:
            return list(self._data.items())
    
    def clear(self):
        with self._lock:
            self._data.clear()
