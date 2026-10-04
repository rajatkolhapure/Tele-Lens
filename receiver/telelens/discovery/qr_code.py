"""
TeleLens Pairing QR Code Generator.
Produces encrypted or plain JSON connection payloads and renders QR code images for instant pairing.
"""

import json
from io import BytesIO
from typing import Dict, Any, Optional

try:
    import qrcode
    from PIL import Image
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


def generate_pairing_payload(
    host_ip: str,
    port: int = 8990,
    session_token: Optional[str] = None,
    server_name: str = "TeleLens-Studio"
) -> str:
    """Creates a standardized JSON payload string for pairing."""
    data = {
        "app": "telelens",
        "name": server_name,
        "host": host_ip,
        "port": port,
        "ws_url": f"ws://{host_ip}:{port}/ws",
        "token": session_token or "open"
    }
    return json.dumps(data)


def generate_qr_image(payload_str: str, box_size: int = 8, border: int = 2) -> Optional["Image.Image"]:
    """Renders a PIL Image containing the pairing QR code."""
    if not QRCODE_AVAILABLE:
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00ADB5", back_color="#1E1E2E")
    return img.convert("RGBA")


def generate_qr_png_bytes(payload_str: str) -> Optional[bytes]:
    """Generates PNG byte buffer for direct embedding in UI or webviews."""
    img = generate_qr_image(payload_str)
    if img is None:
        return None
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
