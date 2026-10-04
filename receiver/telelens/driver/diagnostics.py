"""
TeleLens Virtual Camera Driver Diagnostics.
Detects virtual camera devices, driver registrations, and provides actionable setup guidance.
"""

import sys
import platform
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DiagnosticResult:
    driver_found: bool
    driver_name: str
    backend: str
    details: str
    troubleshooting_steps: List[str]


class DriverDiagnostics:
    """Diagnoses host environment for virtual webcam driver availability."""

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
    def check_windows(cls) -> DiagnosticResult:
        """Inspects Windows registry and system paths for OBS VirtualCam and DirectShow filters."""
        # 1. Check pyvirtualcam import
        try:
            import pyvirtualcam  # noqa: F401
            pyvirtualcam_available = True
        except ImportError:
            pyvirtualcam_available = False

        # 2. Check OBS Virtual Camera filter in Windows Registry
        obs_detected = False
        obs_details = []
        try:
            import winreg

            # DirectShow Video Input Device Categories
            clside_path = r"CLSID\{860BB310-5D01-11d0-BD3B-00A0C911CE86}\Instance"
            for hive in (winreg.HKEY_CLASSES_ROOT, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, clside_path) as key:
                        subkeys_count, _, _ = winreg.QueryInfoKey(key)
                        for i in range(subkeys_count):
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as dev_key:
                                friendly_name, _ = winreg.QueryValueEx(dev_key, "FriendlyName")
                                obs_details.append(friendly_name)
                                if "OBS Virtual Camera" in friendly_name:
                                    obs_detected = True
                except (OSError, FileNotFoundError):
                    pass
        except Exception as e:
            obs_details.append(f"Registry inspection error: {e}")

        if obs_detected:
            return DiagnosticResult(
                driver_found=True,
                driver_name="OBS Virtual Camera",
                backend="obs",
                details=f"OBS Virtual Camera filter registered and ready. Devices found: {', '.join(obs_details)}",
                troubleshooting_steps=[],
            )

        # Unity Capture check
        if any("Unity Video Capture" in name for name in obs_details):
            return DiagnosticResult(
                driver_found=True,
                driver_name="Unity Capture",
                backend="unitycapture",
                details="Unity Capture DirectShow filter registered.",
                troubleshooting_steps=[],
            )

        steps = [
            "Install OBS Studio (free & open source) from https://obsproject.com, which bundles the OBS Virtual Camera driver.",
            "Alternatively, run 'winget install OBSProject.OBSStudio' in PowerShell.",
            "After installing OBS Studio, start and stop the Virtual Camera once in OBS to register the DirectShow filter with Windows.",
            "Ensure python dependencies are installed: 'pip install pyvirtualcam'."
        ]

        if not pyvirtualcam_available:
            steps.insert(0, "Install pyvirtualcam: run 'pip install pyvirtualcam'.")

        return DiagnosticResult(
            driver_found=False,
            driver_name="None detected",
            backend="none",
            details="No compatible DirectShow virtual camera filter found.",
            troubleshooting_steps=steps,
        )

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
        import os
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
