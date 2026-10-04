"""
Tests for UI Stylesheet and Component imports.
"""

import unittest
from telelens.ui.styles.dark_theme import DARK_STYLESHEET


class TestUI(unittest.TestCase):
    def test_stylesheet_defined(self):
        self.assertIn("QMainWindow", DARK_STYLESHEET)
        self.assertIn("#00ADB5", DARK_STYLESHEET)
        self.assertIn("#1E1E2E", DARK_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
