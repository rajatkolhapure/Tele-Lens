"""
TeleLens Turbo Frame Pipe Server (USB Direct Transport).
Receives unthrottled high-bitrate MJPEG / RGB camera frames directly over TCP
via the ADB USB cable bridge, eliminating WebRTC Congestion Control (GCC),
SDP negotiation delay, and UDP wireless leakage.
"""

import struct
import asyncio
import logging
from typing import Callable, Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

MAGIC_HEADER = b"TELE"
HEADER_FORMAT = ">4sIIHBBQ"  # magic (4s), length (I), width (H), height (H), format (B), flags (B), timestamp (Q)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 + 4 + 2 + 2 + 1 + 1 + 8 = 22 bytes

FrameCallback = Callable[[np.ndarray], None]


class TurboStreamServer:
    """
    Dedicated high-throughput TCP server for wired USB frame delivery.
    Bypasses WebRTC entirely to guarantee fixed resolution (e.g. 1088x1088)
    from the very first frame with sub-20ms latency and no bitrate fluctuations.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8991,
        on_frame: Optional[FrameCallback] = None,
        on_connect: Optional[Callable[[str], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self.host = host
        self.port = port
        self.on_frame = on_frame
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self._server: Optional[asyncio.Server] = None
        self._is_streaming = False
        self._frame_count = 0
        self._active_writer: Optional[asyncio.StreamWriter] = None

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def frame_count(self) -> int:
        return self._frame_count

    async def start(self) -> None:
        """Starts the TCP turbo stream listening server."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            reuse_address=True,
        )
        logger.info("TurboStream Direct USB Server listening on tcp://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stops the turbo stream server and terminates active client sockets."""
        self._is_streaming = False
        if self._active_writer:
            try:
                self._active_writer.close()
                await self._active_writer.wait_closed()
            except Exception:
                pass
            self._active_writer = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("TurboStream Direct USB Server stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        client_addr = writer.get_extra_info("peername")
        logger.info("Direct Turbo Frame Client connected from %s", client_addr)
        self._active_writer = writer
        self._is_streaming = True
        self._frame_count = 0

        if self.on_connect:
            self.on_connect(f"{client_addr}")

        try:
            while self._is_streaming:
                # 1. Read frame header
                try:
                    header_bytes = await reader.readexactly(HEADER_SIZE)
                except (asyncio.IncompleteReadError, ConnectionResetError):
                    break

                magic, payload_len, width, height, fmt, flags, timestamp_us = struct.unpack(
                    HEADER_FORMAT, header_bytes
                )

                if magic != MAGIC_HEADER:
                    logger.warning("Invalid magic header received on Turbo pipe: %s", magic)
                    # Resynchronize stream if magic is lost
                    continue

                if payload_len <= 0 or payload_len > 64 * 1024 * 1024:
                    logger.warning("Unreasonable payload length received: %d bytes", payload_len)
                    break

                # 2. Read full frame payload
                payload = await reader.readexactly(payload_len)

                # 3. Decode frame
                rgb_frame = None
                if fmt == 1:  # JPEG Format
                    if CV2_AVAILABLE:
                        buf = np.frombuffer(payload, dtype=np.uint8)
                        bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                        if bgr is not None:
                            rgb_frame = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    else:
                        from PIL import Image
                        import io
                        pil_img = Image.open(io.BytesIO(payload)).convert("RGB")
                        rgb_frame = np.array(pil_img)

                elif fmt == 2:  # Raw RGB24 Format
                    expected_size = width * height * 3
                    if len(payload) == expected_size:
                        rgb_frame = np.frombuffer(payload, dtype=np.uint8).reshape((height, width, 3))

                if rgb_frame is not None:
                    self._frame_count += 1
                    if self.on_frame:
                        self.on_frame(rgb_frame)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in Turbo Frame Stream loop: %s", e)
        finally:
            self._is_streaming = False
            self._active_writer = None
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("Direct Turbo Frame Client disconnected from %s", client_addr)
            if self.on_disconnect:
                self.on_disconnect()
