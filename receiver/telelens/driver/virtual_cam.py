"""
TeleLens Virtual Camera Output Engine.
Encapsulates pyvirtualcam frame publishing, resolution adaptation, and color format conversions.
Optimized with hardware/SIMD OpenCV acceleration for zero-latency publishing.
"""

import logging
import threading
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pyvirtualcam
    from pyvirtualcam import PixelFormat
    PYVIRTUALCAM_AVAILABLE = True
except ImportError:
    PYVIRTUALCAM_AVAILABLE = False
    PixelFormat = None


class VirtualCameraEngine:
    """Manages publishing raw video frames to the OS virtual camera driver with ultra-low latency."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30, backend: str = "auto"):
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
        """Initializes and starts the virtual camera device with auto-detection fallback."""
        if not PYVIRTUALCAM_AVAILABLE:
            logger.error("pyvirtualcam is not installed. Run 'pip install pyvirtualcam'.")
            return False

        with self._lock:
            if self._cam is not None:
                return True

            backends_to_try = []
            if self.backend and self.backend != "auto":
                backends_to_try.append(self.backend)
            backends_to_try.append(None)  # Auto-discovery fallback

            last_err = None
            for b in backends_to_try:
                try:
                    self._cam = pyvirtualcam.Camera(
                        width=self.width,
                        height=self.height,
                        fps=self.fps,
                        fmt=PixelFormat.RGB,
                        backend=b,
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
                    last_err = e
                    continue

            logger.error("Failed to start virtual camera: %s", last_err)
            self._cam = None
            self._is_running = False
            return False

    def send_frame(self, frame_rgb: np.ndarray) -> bool:
        """
        Sends an RGB numpy array frame (H, W, 3) to the virtual camera.
        High-speed adaptation using OpenCV SIMD without blocking sleeps.
        """
        with self._lock:
            if not self._is_running or self._cam is None:
                return False

            try:
                h, w = frame_rgb.shape[:2]
                if (w, h) != (self.width, self.height):
                    if CV2_AVAILABLE:
                        interpolation = cv2.INTER_AREA if (w > self.width and h > self.height) else cv2.INTER_LINEAR
                        frame_rgb = cv2.resize(frame_rgb, (self.width, self.height), interpolation=interpolation)
                    else:
                        from PIL import Image
                        pil_img = Image.fromarray(frame_rgb)
                        resized_img = pil_img.resize((self.width, self.height), Image.Resampling.BILINEAR)
                        frame_rgb = np.ascontiguousarray(np.array(resized_img))

                if not frame_rgb.flags.c_contiguous:
                    frame_rgb = np.ascontiguousarray(frame_rgb)

                self._cam.send(frame_rgb)
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
