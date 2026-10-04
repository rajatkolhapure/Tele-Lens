"""
TeleLens Camera Controls Protocol Handler.
Serializes remote hardware commands sent over WebRTC DataChannel.
"""

import json
from enum import Enum
from typing import Dict, Any, Optional


class CameraLens(str, Enum):
    REAR_MAIN = "rear_main"
    REAR_ULTRAWIDE = "rear_ultrawide"
    REAR_TELEPHOTO = "rear_telephoto"
    FRONT = "front"


class CameraControls:
    """Helper to construct JSON-RPC DataChannel messages for phone sensor control."""

    @staticmethod
    def set_torch(enabled: bool) -> str:
        return json.dumps({
            "method": "camera.setTorch",
            "params": {"enabled": enabled}
        })

    @staticmethod
    def set_lens(lens: CameraLens) -> str:
        return json.dumps({
            "method": "camera.setLens",
            "params": {"lens": str(lens.value if isinstance(lens, CameraLens) else lens)}
        })

    @staticmethod
    def set_zoom(zoom_factor: float) -> str:
        """Sets digital/optical zoom level (e.g. 1.0 to 10.0)."""
        return json.dumps({
            "method": "camera.setZoom",
            "params": {"zoom": float(zoom_factor)}
        })

    @staticmethod
    def set_exposure(iso: Optional[int] = None, shutter_speed_us: Optional[int] = None, auto: bool = True) -> str:
        params: Dict[str, Any] = {"auto": auto}
        if not auto:
            if iso is not None:
                params["iso"] = iso
            if shutter_speed_us is not None:
                params["shutter_speed_us"] = shutter_speed_us
        return json.dumps({
            "method": "camera.setExposure",
            "params": params
        })

    @staticmethod
    def set_focus(distance: float, auto: bool = True) -> str:
        """Sets focus distance from 0.0 (near/macro) to 1.0 (infinity), or auto-focus."""
        return json.dumps({
            "method": "camera.setFocus",
            "params": {"auto": auto, "distance": float(distance)}
        })

    @staticmethod
    def set_thermal_saver(enabled: bool) -> str:
        return json.dumps({
            "method": "camera.setThermalSaver",
            "params": {"enabled": enabled}
        })
