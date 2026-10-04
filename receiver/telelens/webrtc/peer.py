"""
TeleLens WebRTC Peer Connection Manager.
Manages media track demuxing, video frame routing, audio loopback, and DataChannel control commands.
"""

import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
    from aiortc.contrib.media import MediaRelay
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    RTCSessionDescription = None
    RTCIceCandidate = None

FrameCallback = Callable[[np.ndarray], None]
TelemetryCallback = Callable[[Dict[str, Any]], None]


class WebRTCPeerManager:
    """Manages an active WebRTC session between the phone and laptop receiver."""

    def __init__(
        self,
        on_frame: Optional[FrameCallback] = None,
        on_telemetry: Optional[TelemetryCallback] = None
    ):
        self.on_frame = on_frame
        self.on_telemetry = on_telemetry
        self.pc: Optional["RTCPeerConnection"] = None
        self.data_channel = None
        self._is_connected = False
        self._video_track = None
        self._audio_track = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def handle_offer(self, sdp_type: str, sdp_string: str) -> str:
        """Processes remote offer SDP and returns local answer SDP."""
        if not AIORTC_AVAILABLE:
            raise RuntimeError("aiortc is not installed. Run 'pip install aiortc'.")

        self.pc = RTCPeerConnection()

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self.data_channel = channel
            logger.info("WebRTC DataChannel established: %s", channel.label)

            @channel.on("message")
            def on_message(message):
                try:
                    data = json.loads(message)
                    if self.on_telemetry:
                        self.on_telemetry(data)
                except Exception as e:
                    logger.warning("Error processing DataChannel message: %s", e)

        @self.pc.on("track")
        def on_track(track):
            logger.info("Received WebRTC media track: %s (kind: %s)", track.id, track.kind)
            if track.kind == "video":
                self._video_track = track
                asyncio.create_task(self._process_video_track(track))
            elif track.kind == "audio":
                self._audio_track = track
                asyncio.create_task(self._process_audio_track(track))

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("Connection state changed: %s", self.pc.connectionState)
            self._is_connected = (self.pc.connectionState == "connected")

        offer = RTCSessionDescription(sdp=sdp_string, type=sdp_type)
        await self.pc.setRemoteDescription(offer)

        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return self.pc.localDescription.sdp

    async def _process_video_track(self, track) -> None:
        """Continuously pulls frames from the video track and dispatches to frame callback."""
        try:
            while True:
                frame = await track.recv()
                # Convert PyAV VideoFrame to RGB numpy array
                img_rgb = frame.to_ndarray(format="rgb24")
                if self.on_frame:
                    self.on_frame(img_rgb)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Video track reader stopped: %s", e)

    async def _process_audio_track(self, track) -> None:
        """Continuously pulls audio frames for virtual microphone loopback."""
        try:
            while True:
                _ = await track.recv()
                # Audio frame processing can route to virtual audio device
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Audio track reader stopped: %s", e)

    def send_control(self, command_json: str) -> bool:
        """Sends a JSON-RPC control command over DataChannel to the phone."""
        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(command_json)
            return True
        logger.warning("Cannot send command: DataChannel is not open.")
        return False

    async def close(self) -> None:
        """Closes the WebRTC peer connection and releases resources."""
        if self.pc:
            try:
                await self.pc.close()
            except Exception as e:
                logger.warning("Error closing RTCPeerConnection: %s", e)
            finally:
                self.pc = None
                self.data_channel = None
                self._is_connected = False
                logger.info("WebRTCPeerManager closed.")
