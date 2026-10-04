"""
TeleLens Configuration Module.
Handles system configuration, default streaming presets, and device preferences.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class StreamConfig:
    width: int = 3840
    height: int = 2160
    fps: int = 30
    bitrate_kbps: int = 35000  # High bitrate for 4K studio quality
    backend: str = "obs"       # 'obs', 'unitycapture', or 'v4l2loopback'
    audio_enabled: bool = True
    device_name: str = "TeleLens Virtual Camera"

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    signaling_port: int = 8990
    mdns_service_name: str = "TeleLens-Studio"
    mdns_service_type: str = "_telelens._tcp.local."
    require_approval: bool = True
    session_timeout_seconds: int = 300


@dataclass
class TeleLensConfig:
    stream: StreamConfig = field(default_factory=StreamConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    theme: str = "dark"
    log_level: str = "INFO"
