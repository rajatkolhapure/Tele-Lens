"""
Tests for TeleLens WebRTC Resolution Pipeline, SDP Negotiation, and Virtual Camera.
"""

import unittest
import numpy as np
from telelens.webrtc.peer import WebRTCPeerManager
from telelens.driver.virtual_cam import VirtualCameraEngine, OPENCV_AVAILABLE


class TestWebRTCResolutionPipeline(unittest.TestCase):
    def setUp(self):
        self.peer_mgr = WebRTCPeerManager()

    def test_sdp_munging_prioritizes_h264_and_upgrades_level(self):
        sample_sdp = (
            "v=0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 97 98 99 100 101 102\r\n"
            "a=rtpmap:97 VP8/90000\r\n"
            "a=rtpmap:98 rtx/90000\r\n"
            "a=rtpmap:99 H264/90000\r\n"
            "a=fmtp:99 profile-level-id=42001f\r\n"
            "a=rtpmap:100 rtx/90000\r\n"
            "a=rtpmap:101 H264/90000\r\n"
            "a=fmtp:101 profile-level-id=42e01f\r\n"
            "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
            "a=rtpmap:111 opus/48000/2\r\n"
        )

        munged = self.peer_mgr._munge_answer_sdp(sample_sdp)
        lines = munged.split("\r\n")

        # 1. m=video line must have H.264 payload types (99, 101) BEFORE VP8 (97)
        video_line = next(ln for ln in lines if ln.startswith("m=video"))
        pts = video_line.split()[3:]
        self.assertIn("99", pts)
        self.assertIn("101", pts)
        self.assertIn("97", pts)
        self.assertLess(pts.index("99"), pts.index("97"), "H.264 PT 99 must precede VP8 PT 97")
        self.assertLess(pts.index("101"), pts.index("97"), "H.264 PT 101 must precede VP8 PT 97")

        # 2. Bitrate descriptors must be injected (50 Mbps floor)
        self.assertIn("b=AS:50000", lines)
        self.assertIn("b=TIAS:50000000", lines)

        # 3. profile-level-id must be upgraded from Level 3.1 to Level 5.1 (42e033)
        fmtp_99 = next(ln for ln in lines if ln.startswith("a=fmtp:99"))
        self.assertIn("profile-level-id=42e033", fmtp_99)
        self.assertIn("level-asymmetry-allowed=1", fmtp_99)
        self.assertIn("packetization-mode=1", fmtp_99)

        fmtp_101 = next(ln for ln in lines if ln.startswith("a=fmtp:101"))
        self.assertIn("profile-level-id=42e033", fmtp_101)

    def test_opencv_available_and_fast_scaling(self):
        self.assertTrue(OPENCV_AVAILABLE, "opencv-python should be available for SIMD scaling")
        import cv2
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        resized = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)
        self.assertEqual(resized.shape, (1080, 1920, 3))

    def test_virtual_camera_dimensions(self):
        engine = VirtualCameraEngine(width=1920, height=1080, fps=30)
        self.assertEqual(engine.width, 1920)
        self.assertEqual(engine.height, 1080)
        self.assertFalse(engine.is_running)


if __name__ == "__main__":
    unittest.main()
