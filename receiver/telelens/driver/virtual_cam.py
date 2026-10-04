"""
TeleLens Virtual Camera Output Engine.
Encapsulates pyvirtualcam frame publishing, resolution adaptation, and color format conversions.
"""

import logging
import threading
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    import pyvirtualcam
    from pyvirtualcam import PixelFormat
    PYVIRTUALCAM_AVAILABLE = True
except ImportError:
    PYVIRTUALCAM_AVAILABLE = False
    PixelFormat = None


class VirtualCameraEngine:
    """Manages publishing raw video frames to the OS virtual camera driver."""

    def __init__(self, width: int = 3840, height: int = 2160, fps: int = 30, backend: str = "obs"):
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = backend
        self._cam: Optional["pyvirtualcam.Camera"] = None
        self._lock = threading.Lock()
        self._is_running = False
        self._frame_count = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def start(self) -> bool:
        """Initializes and starts the virtual camera device."""
        if not PYVIRTUALCAM_AVAILABLE:
            logger.error("pyvirtualcam is not installed. Run 'pip install pyvirtualcam'.")
            return False

        with self._lock:
            if self._cam is not None:
                return True

            try:
                # pyvirtualcam uses RGB format by default
                self._cam = pyvirtualcam.Camera(
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    fmt=PixelFormat.RGB,
                    backend=self.backend if self.backend != "auto" else None,
                )
                self._is_running = True
                self._frame_count = 0
                logger.info(
                    "Virtual camera started: %s (%dx%d @ %d FPS, backend: %s)",
                    self._cam.device,
                    self.width,
                    self.height,
                    self.fps,
                    self._cam.backend,
                )
                return True
            except Exception as e:
                logger.error("Failed to start virtual camera: %s", e)
                self._cam = None
                self._is_running = False
                return False

    def send_frame(self, frame_rgb: np.ndarray) -> bool:
        """
        Sends an RGB numpy array frame (H, W, 3) to the virtual camera.
        Automatically resizes if input dimensions differ from the virtual camera buffer.
        """
        with self._lock:
            if not self._is_running or self._cam is None:
                return False

            try:
                # Validate or adapt resolution
                h, w, c = frame_rgb.shape
                if (w, h) != (self.width, self.height):
                    import cv2
                    frame_rgb = cv2.resize(frame_rgb, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

                self._cam.send(frame_rgb)
                self._cam.sleep_until_next_frame()
                self._frame_count += 1
                return True
            except Exception as e:
                logger.error("Error pushing frame to virtual camera: %s", e)
                return False

    def resize(self, new_width: int, new_height: int, new_fps: Optional[int] = None) -> bool:
        """Closes existing camera and reopens with new resolution."""
        with self._lock:
            self.stop()
            self.width = new_width
            self.height = new_height
            if new_fps:
                self.fps = new_fps
            return self.start()

    def stop(self) -> None:
        """Closes and releases the virtual camera driver."""
        with self._lock:
            if self._cam is not None:
                try:
                    self._cam.close()
                except Exception as e:
                    logger.warning("Error closing virtual camera: %s", e)
                finally:
                    self._cam = None
                    self._is_running = False
                    logger.info("Virtual camera stopped.")
