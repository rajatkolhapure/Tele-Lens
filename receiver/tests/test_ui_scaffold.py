"""
Tests for UI Stylesheet and Component imports.
"""

import unittest
from telelens.ui.styles.dark_theme import DARK_STYLESHEET


class TestUI(unittest.TestCase):
    def test_stylesheet_defined(self):
        self.assertIn("QMainWindow", DARK_STYLESHEET)
        self.assertIn("#09090B", DARK_STYLESHEET)
        self.assertIn("#121214", DARK_STYLESHEET)
        self.assertIn("#E4E4E7", DARK_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
