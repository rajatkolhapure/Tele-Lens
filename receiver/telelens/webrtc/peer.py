"""
TeleLens WebRTC Peer Connection Manager.
Manages media track demuxing, video frame routing, audio loopback, and DataChannel control commands.
Optimized with high initial bitrate floors to prevent Google Congestion Control (GCC) ramp-up delays.
"""

import re
import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    RTCSessionDescription = None
    RTCIceCandidate = None

FrameCallback = Callable[[np.ndarray], None]
TelemetryCallback = Callable[[Dict[str, Any]], None]
ControlCallback = Callable[[str, Dict[str, Any]], None]


class WebRTCPeerManager:
    """Manages an active WebRTC session between the phone and laptop receiver."""

    def __init__(
        self,
        on_frame: Optional[FrameCallback] = None,
        on_telemetry: Optional[TelemetryCallback] = None,
        on_remote_disconnect: Optional[Callable[[], None]] = None,
        on_remote_control: Optional[ControlCallback] = None
    ):
        self.on_frame = on_frame
        self.on_telemetry = on_telemetry
        self.on_remote_disconnect = on_remote_disconnect
        self.on_remote_control = on_remote_control
        self.pc: Optional["RTCPeerConnection"] = None
        self.data_channel = None
        self._is_connected = False
        self._video_track = None
        self._audio_track = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _munge_answer_sdp(self, sdp: str) -> str:
        """
        Injects high bitrate and bandwidth parameters into SDP answer.
        Prioritizes H.264 over VP8 and upgrades profile-level-id to Level 5.1 (42e033)
        with an aggressive bitrate floor (25-35 Mbps) to eliminate downscaling and slow probing.
        """
        lines = sdp.split("\r\n")
        output = []
        in_video_section = False

        # First pass: find all H.264 payload types
        h264_pts = set()
        for line in lines:
            if line.startswith("a=rtpmap:") and "H264/90000" in line:
                try:
                    pt = line.split()[0].split(":")[1]
                    h264_pts.add(pt)
                except Exception:
                    pass

        for line in lines:
            if line.startswith("m=video"):
                in_video_section = True
                parts = line.split()
                if len(parts) > 3 and h264_pts:
                    # Reorder payload types so H.264 is the primary offered codec
                    pts = parts[3:]
                    reordered = [p for p in pts if p in h264_pts] + [p for p in pts if p not in h264_pts]
                    output.append(f"{parts[0]} {parts[1]} {parts[2]} {' '.join(reordered)}")
                else:
                    output.append(line)
                output.append("b=AS:50000")
                output.append("b=TIAS:50000000")
                continue
            elif line.startswith("m=audio") or line.startswith("m=application"):
                in_video_section = False

            if in_video_section and line.startswith("a=fmtp:"):
                modified = line
                if "profile-level-id=" in modified:
                    # Upgrade from Level 3.1 (42001f / 42e01f) to Level 5.1 (42e033)
                    modified = re.sub(r'profile-level-id=[0-9a-fA-F]+', 'profile-level-id=42e033', modified)
                    if "level-asymmetry-allowed" not in modified:
                        modified += ";level-asymmetry-allowed=1"
                    if "packetization-mode" not in modified:
                        modified += ";packetization-mode=1"
                output.append(f"{modified};x-google-min-bitrate=25000;x-google-start-bitrate=35000;x-google-max-bitrate=50000")
            else:
                output.append(line)

        return "\r\n".join(output)

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
                    if isinstance(data, dict):
                        method = data.get("method")
                        params = data.get("params", {})
                        if method == "session.disconnect":
                            logger.info("Remote phone initiated session disconnect.")
                            if self.on_remote_disconnect:
                                self.on_remote_disconnect()
                        elif method and self.on_remote_control:
                            self.on_remote_control(method, params)
                        elif self.on_telemetry:
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

        # Prioritize hardware H.264 on transceivers
        for transceiver in self.pc.getTransceivers():
            if transceiver.kind == "video":
                try:
                    from aiortc import RTCRtpReceiver
                    caps = RTCRtpReceiver.getCapabilities("video")
                    h264_codecs = [c for c in caps.codecs if c.mimeType.lower() == "video/h264"]
                    vp8_codecs = [c for c in caps.codecs if c.mimeType.lower() == "video/vp8"]
                    if h264_codecs:
                        transceiver.setCodecPreferences(h264_codecs + vp8_codecs)
                except Exception as pref_err:
                    logger.debug("Failed setting transceiver codec preferences: %s", pref_err)

        answer = await self.pc.createAnswer()
        munged_sdp = self._munge_answer_sdp(answer.sdp)
        custom_answer = RTCSessionDescription(sdp=munged_sdp, type=answer.type)
        await self.pc.setLocalDescription(custom_answer)

        return self.pc.localDescription.sdp

    async def _process_video_track(self, track) -> None:
        """Continuously pulls frames from the video track and dispatches to frame callback."""
        try:
            while True:
                frame = await track.recv()
                img_rgb = np.ascontiguousarray(frame.to_ndarray(format="rgb24")).copy()
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
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Audio track reader stopped: %s", e)

    async def close(self) -> None:
        """Closes the WebRTC peer connection and releases resources."""
        if self.pc is not None:
            await self.pc.close()
            self.pc = None
            self._is_connected = False
            self.data_channel = None
            logger.info("WebRTC Peer Connection closed.")
