"""
TeleLens mDNS Service Discovery (Zeroconf).
Advertises the laptop's receiver port over local Wi-Fi LAN for instant auto-discovery by the Flutter mobile app.
"""

import socket
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False


def get_local_ip_addresses() -> List[str]:
    """Retrieves all non-loopback IPv4 addresses of the host machine."""
    ip_list = []
    try:
        # Standard UDP connect technique to detect default outbound interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        ip_list.append(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip not in ip_list and not ip.startswith("127."):
                ip_list.append(ip)
    except Exception:
        pass

    if not ip_list:
        ip_list.append("127.0.0.1")

    return ip_list


class TeleLensMDNSService:
    """Manages mDNS advertisement of the TeleLens receiver."""

    def __init__(self, port: int = 8990, service_name: str = "TeleLens-Studio"):
        self.port = port
        self.service_name = service_name
        self.service_type = "_telelens._tcp.local."
        self._zeroconf: Optional["Zeroconf"] = None
        self._service_info: Optional["ServiceInfo"] = None

    def start(self) -> bool:
        if not ZEROCONF_AVAILABLE:
            logger.warning("zeroconf library not available. mDNS discovery disabled.")
            return False

        try:
            local_ips = get_local_ip_addresses()
            primary_ip = local_ips[0]

            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._service_info = ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                addresses=[socket.inet_aton(primary_ip)],
                port=self.port,
                properties={
                    b"version": b"0.1.0",
                    b"protocol": b"webrtc",
                    b"studio": b"true"
                },
                server=f"{socket.gethostname()}.local.",
            )
            self._zeroconf.register_service(self._service_info)
            logger.info("mDNS service registered: %s on %s:%d", self.service_name, primary_ip, self.port)
            return True
        except Exception as e:
            logger.error("Failed to register mDNS service: %s", e)
            return False

    def stop(self) -> None:
        if self._zeroconf and self._service_info:
            try:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
                logger.info("mDNS service unregistered.")
            except Exception as e:
                logger.warning("Error unregistering mDNS service: %s", e)
            finally:
                self._zeroconf = None
                self._service_info = None
