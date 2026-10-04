"""
Tests for Virtual Camera Driver Diagnostics.
"""

import unittest
from telelens.driver.diagnostics import DriverDiagnostics, DiagnosticResult


class TestDriverDiagnostics(unittest.TestCase):
    def test_diagnostics_returns_result(self):
        res = DriverDiagnostics.run_all()
        self.assertIsInstance(res, DiagnosticResult)
        self.assertIsInstance(res.driver_found, bool)
        self.assertIsInstance(res.driver_name, str)
        self.assertIsInstance(res.backend, str)
        self.assertIsInstance(res.troubleshooting_steps, list)


if __name__ == "__main__":
    unittest.main()
