"""
TeleLens Virtual Camera Driver Diagnostics & Auto-Registration.
Detects virtual camera devices, driver registrations, and provides 1-click administrative driver setup.
"""

import os
import sys
import platform
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except Exception:
    pass


@dataclass
class DiagnosticResult:
    driver_found: bool
    driver_name: str
    backend: str
    details: str
    troubleshooting_steps: List[str]
    can_auto_register: bool = False
    dll_path_to_register: Optional[str] = None


class DriverDiagnostics:
    """Diagnoses host environment for virtual webcam driver availability and provides elevation actions."""

    @classmethod
    def run_all(cls) -> DiagnosticResult:
        os_name = platform.system().lower()
        if os_name == "windows":
            return cls.check_windows()
        elif os_name == "linux":
            return cls.check_linux()
        elif os_name == "darwin":
            return cls.check_macos()
        else:
            return DiagnosticResult(
                driver_found=False,
                driver_name="Unknown OS",
                backend="none",
                details=f"Unsupported OS: {platform.system()}",
                troubleshooting_steps=["TeleLens supports Windows, Linux, and macOS."],
            )

    @classmethod
    def get_candidate_driver_dll(cls) -> Optional[str]:
        """Locates available 64-bit OBS virtual camera DLL on host machine or workspace."""
        candidates = [
            r"C:\Program Files\obs-studio\data\obs-plugins\win-dshow\obs-virtualcam-module64.dll",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "installer", "drivers", "obs-virtualcam", "obs-virtualcam-startup.dll")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drivers", "obs-virtualcam-startup.dll")),
        ]
        for path in candidates:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return path
        return None

    @classmethod
    def check_windows(cls) -> DiagnosticResult:
        """Inspects Windows registry, installed PnP cameras, and system paths for OBS VirtualCam."""
        try:
            import pyvirtualcam  # noqa: F401
            pyvirtualcam_available = True
        except ImportError:
            pyvirtualcam_available = False

        obs_detected = False
        obs_details = []

        # 1. Check OBS DirectShow & Media Foundation CLSIDs in Registry
        try:
            import winreg

            # Direct check for primary OBS filter CLSID
            for hive in (winreg.HKEY_CLASSES_ROOT, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Classes\CLSID\{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"):
                        obs_detected = True
                        obs_details.append("OBS Virtual Camera Filter (CLSID {A3FCE0F5...}) registered in Registry.")
                        break
                except (OSError, FileNotFoundError):
                    pass

            # DirectShow Video Input Device Categories
            clside_path = r"CLSID\{860BB310-5D01-11d0-BD3B-00A0C911CE86}\Instance"
            for hive in (winreg.HKEY_CLASSES_ROOT, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, clside_path) as key:
                        subkeys_count, _, _ = winreg.QueryInfoKey(key)
                        for i in range(subkeys_count):
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as dev_key:
                                try:
                                    friendly_name, _ = winreg.QueryValueEx(dev_key, "FriendlyName")
                                    obs_details.append(friendly_name)
                                    if "OBS Virtual Camera" in friendly_name or "OBS-Camera" in friendly_name:
                                        obs_detected = True
                                except OSError:
                                    pass
                except (OSError, FileNotFoundError):
                    pass
        except Exception as e:
            obs_details.append(f"Registry inspection error: {e}")

        # Check candidate DLL on disk
        candidate_dll = cls.get_candidate_driver_dll()
        can_auto_register = candidate_dll is not None

        if obs_detected:
            return DiagnosticResult(
                driver_found=True,
                driver_name="OBS Virtual Camera",
                backend="obs",
                details=f"OBS Virtual Camera filter registered and active in Windows. (Detected: {', '.join(set(obs_details))})",
                troubleshooting_steps=[
                    "Virtual camera driver is registered and ready for Zoom, Microsoft Teams, Google Meet, and Discord.",
                    "For modern UWP apps like the Windows Camera app: Windows Camera app only enumerates Media Foundation devices. Standard Win32/DirectShow apps recognize OBS Virtual Camera immediately."
                ],
                can_auto_register=can_auto_register,
                dll_path_to_register=candidate_dll,
            )

        # Check Unity Capture
        if any("Unity Video Capture" in name for name in obs_details):
            return DiagnosticResult(
                driver_found=True,
                driver_name="Unity Capture",
                backend="unitycapture",
                details="Unity Capture DirectShow filter registered.",
                troubleshooting_steps=[],
                can_auto_register=False,
            )

        steps = []
        if can_auto_register:
            steps.append(f"Driver DLL found on your PC at: {candidate_dll}. Click 'Register Driver (Administrator)' below to install with 1 click.")
        else:
            steps.append("Install OBS Studio from https://obsproject.com, or install the TeleLens Windows Installer which bundles the driver.")

        steps.append("DirectShow Virtual Cameras vs Modern Windows Camera App: Apps like Iriun Webcam install kernel-mode AVStream hardware drivers; OBS Virtual Camera installs a DirectShow filter. Applications such as Zoom, Teams, Google Meet, OBS, Discord, and Chrome support OBS Virtual Camera.")

        if not pyvirtualcam_available:
            steps.append("Ensure pyvirtualcam is installed: run 'pip install pyvirtualcam'.")

        return DiagnosticResult(
            driver_found=False,
            driver_name="None detected",
            backend="obs",
            details="OBS Virtual Camera DirectShow filter is not registered in the Windows Registry.",
            troubleshooting_steps=steps,
            can_auto_register=can_auto_register,
            dll_path_to_register=candidate_dll,
        )

    @classmethod
    def register_driver_elevated(cls) -> bool:
        """Executes regsvr32 with administrator elevation (UAC prompt) to register the virtual camera DLL."""
        dll_path = cls.get_candidate_driver_dll()
        if not dll_path:
            return False

        try:
            # Check if OBS virtualcam-install.bat exists
            obs_bat = r"C:\Program Files\obs-studio\data\obs-plugins\win-dshow\virtualcam-install.bat"
            if os.path.exists(obs_bat):
                cmd = f'Start-Process -FilePath cmd.exe -ArgumentList "/c \\"{obs_bat}\\"" -Verb RunAs -Wait'
            else:
                cmd = f'Start-Process -FilePath "regsvr32.exe" -ArgumentList \'/i /s "{dll_path}"\' -Verb RunAs -Wait'

            res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
            return res.returncode == 0
        except Exception as e:
            if logger:
                logger.error("Failed to run elevated driver registration: %s", e)
            return False

    @classmethod
    def check_linux(cls) -> DiagnosticResult:
        """Checks for /dev/video* devices and v4l2loopback kernel module."""
        try:
            output = subprocess.check_output(["lsmod"], text=True)
            if "v4l2loopback" in output:
                return DiagnosticResult(
                    driver_found=True,
                    driver_name="v4l2loopback",
                    backend="v4l2loopback",
                    details="Kernel module v4l2loopback is loaded.",
                    troubleshooting_steps=[],
                )
        except Exception:
            pass

        return DiagnosticResult(
            driver_found=False,
            driver_name="None detected",
            backend="v4l2loopback",
            details="v4l2loopback kernel module not loaded.",
            troubleshooting_steps=[
                "Install v4l2loopback: 'sudo apt install v4l2loopback-dkms'",
                "Load the kernel module: 'sudo modprobe v4l2loopback devices=1 video_nr=10 card_label=\"TeleLens Virtual Cam\" exclusive_caps=1'"
            ],
        )

    @classmethod
    def check_macos(cls) -> DiagnosticResult:
        """Checks for OBS virtual camera on macOS."""
        obs_mac_plugin = "/Library/CoreMediaIO/Plug-Ins/DAL/obs-mac-virtualcam.plugin"
        if os.path.exists(obs_mac_plugin):
            return DiagnosticResult(
                driver_found=True,
                driver_name="OBS macOS Virtual Camera",
                backend="obs",
                details=f"Found plugin at {obs_mac_plugin}",
                troubleshooting_steps=[],
            )
        return DiagnosticResult(
            driver_found=False,
            driver_name="None detected",
            backend="obs",
            details="OBS macOS Virtual Camera DAL plugin not found.",
            troubleshooting_steps=[
                "Install OBS Studio from https://obsproject.com",
                "Launch OBS Studio and start the Virtual Camera once to install system extension."
            ],
        )


def main():
    print("=" * 60)
    print("  TeleLens Virtual Camera Driver Diagnostic Utility")
    print("=" * 60)
    result = DriverDiagnostics.run_all()
    print(f"Platform       : {platform.system()} {platform.release()}")
    print(f"Driver Found   : {'[YES]' if result.driver_found else '[NO]'}")
    print(f"Driver Name    : {result.driver_name}")
    print(f"Backend Target : {result.backend}")
    print(f"Details        : {result.details}")
    if result.can_auto_register:
        print(f"Candidate DLL  : {result.dll_path_to_register}")

    if not result.driver_found:
        print("\nTroubleshooting & Setup Instructions:")
        for idx, step in enumerate(result.troubleshooting_steps, 1):
            print(f"  {idx}. {step}")
        sys.exit(1)
    else:
        print("\nVirtual camera pipeline is ready for 4K/1440p streaming!")
        sys.exit(0)


if __name__ == "__main__":
    main()
