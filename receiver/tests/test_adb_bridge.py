"""
Tests for ADB Bridge Cable Manager.
"""

import unittest
from telelens.discovery.adb_bridge import ADBBridge


class TestADBBridge(unittest.TestCase):
    def test_adb_bridge_initialization(self):
        bridge = ADBBridge(port=8990)
        self.assertEqual(bridge.port, 8990)
        # Should detect adb if installed or return None gracefully
        self.assertIsInstance(bridge.is_available, bool)

    def test_list_devices_type(self):
        bridge = ADBBridge(port=8990)
        devices = bridge.list_devices()
        self.assertIsInstance(devices, list)


if __name__ == "__main__":
    unittest.main()
