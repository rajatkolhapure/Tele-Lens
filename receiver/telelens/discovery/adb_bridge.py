"""
TeleLens ADB Cable Reverse Port Forwarding Manager.
Automatically detects ADB and configures port reversal so wired USB streaming works seamlessly.
"""

import os
import shutil
import subprocess
import logging
import threading
import time
from typing import Optional, List

logger = logging.getLogger(__name__)

# Windows creation flag to prevent console window popup
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class ADBBridge:
    """Manages ADB reverse port-forwarding for USB cable connections."""

    def __init__(self, port: int = 8990):
        self.port = port
        self.adb_path: Optional[str] = self._locate_adb()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _locate_adb(self) -> Optional[str]:
        """Locates adb executable on the host system."""
        # Check PATH first
        path_adb = shutil.which("adb")
        if path_adb:
            return path_adb

        # Check standard Windows paths
        if os.name == "nt":
            candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Android\platform-tools\adb.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Android\platform-tools\adb.exe"),
                r"C:\platform-tools\adb.exe",
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    return candidate

        # Check macOS / Linux paths
        candidates_unix = [
            os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
            os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
            "/usr/bin/adb",
            "/usr/local/bin/adb",
        ]
        for candidate in candidates_unix:
            if os.path.isfile(candidate):
                return candidate

        return None

    @property
    def is_available(self) -> bool:
        return self.adb_path is not None

    def list_devices(self) -> List[str]:
        """Returns list of connected ADB device serial numbers."""
        if not self.adb_path:
            return []
        try:
            res = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=CREATE_NO_WINDOW,
            )
            devices = []
            for line in res.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices
        except Exception as e:
            logger.debug("ADB list devices failed: %s", e)
            return []

    def reverse_port(self) -> bool:
        """Executes adb reverse tcp:PORT tcp:PORT for connected devices."""
        if not self.adb_path:
            return False
        try:
            res = subprocess.run(
                [self.adb_path, "reverse", f"tcp:{self.port}", f"tcp:{self.port}"],
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=CREATE_NO_WINDOW,
            )
            if res.returncode == 0:
                logger.info("ADB port reversed: tcp:%d -> tcp:%d", self.port, self.port)
                return True
        except Exception as e:
            logger.debug("ADB reverse failed: %s", e)
        return False

    def start_auto_reverse(self, interval_seconds: int = 4) -> None:
        """Starts a background monitor that ensures ADB port reverse is active."""
        if self._running or not self.adb_path:
            return

        self._running = True

        def loop():
            logger.info("ADB Auto-Reverse monitor started (using %s)", self.adb_path)
            last_device_count = 0
            while self._running:
                try:
                    devices = self.list_devices()
                    if devices and (len(devices) != last_device_count or not self.reverse_port()):
                        self.reverse_port()
                    last_device_count = len(devices)
                except Exception as e:
                    logger.debug("ADB monitor tick error: %s", e)
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=loop, daemon=True, name="TeleLens-ADB-Bridge")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
