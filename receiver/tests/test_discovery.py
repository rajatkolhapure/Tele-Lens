"""
Tests for discovery and QR code payload generation.
"""

import json
import unittest
from telelens.discovery.qr_code import generate_pairing_payload
from telelens.discovery.mdns import get_local_ip_addresses


class TestDiscovery(unittest.TestCase):
    def test_pairing_payload_json(self):
        payload = generate_pairing_payload(host_ip="192.168.1.100", port=8990, session_token="tok_123")
        data = json.loads(payload)
        self.assertEqual(data["app"], "telelens")
        self.assertEqual(data["host"], "192.168.1.100")
        self.assertEqual(data["port"], 8990)
        self.assertEqual(data["token"], "tok_123")
        self.assertEqual(data["ws_url"], "ws://192.168.1.100:8990/ws")

    def test_get_local_ip_addresses(self):
        ips = get_local_ip_addresses()
        self.assertIsInstance(ips, list)
        self.assertGreater(len(ips), 0)


if __name__ == "__main__":
    unittest.main()
