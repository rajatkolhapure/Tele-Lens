"""
Tests for TeleLens Configuration.
"""

import unittest
from telelens.config import TeleLensConfig, StreamConfig, ServerConfig


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = TeleLensConfig()
        self.assertEqual(config.stream.width, 3840)
        self.assertEqual(config.stream.height, 2160)
        self.assertEqual(config.stream.fps, 30)
        self.assertEqual(config.stream.resolution, (3840, 2160))
        self.assertEqual(config.server.signaling_port, 8990)
        self.assertTrue(config.server.require_approval)

    def test_custom_stream_config(self):
        stream = StreamConfig(width=2560, height=1440, fps=60)
        self.assertEqual(stream.resolution, (2560, 1440))
        self.assertEqual(stream.fps, 60)


if __name__ == "__main__":
    unittest.main()
