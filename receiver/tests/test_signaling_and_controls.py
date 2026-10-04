"""
Tests for TeleLens Signaling Server, Gatekeeper Approval, and Camera Controls.
"""

import json
import asyncio
import unittest
from telelens.webrtc.controls import CameraControls, CameraLens
from telelens.webrtc.signaling import SignalingServer


class TestCameraControls(unittest.TestCase):
    def test_torch_control(self):
        cmd = json.loads(CameraControls.set_torch(True))
        self.assertEqual(cmd["method"], "camera.setTorch")
        self.assertTrue(cmd["params"]["enabled"])

    def test_lens_control(self):
        cmd = json.loads(CameraControls.set_lens(CameraLens.REAR_ULTRAWIDE))
        self.assertEqual(cmd["method"], "camera.setLens")
        self.assertEqual(cmd["params"]["lens"], "rear_ultrawide")

    def test_zoom_control(self):
        cmd = json.loads(CameraControls.set_zoom(2.5))
        self.assertEqual(cmd["method"], "camera.setZoom")
        self.assertAlmostEqual(cmd["params"]["zoom"], 2.5)

    def test_exposure_control(self):
        cmd = json.loads(CameraControls.set_exposure(iso=400, shutter_speed_us=20000, auto=False))
        self.assertEqual(cmd["method"], "camera.setExposure")
        self.assertFalse(cmd["params"]["auto"])
        self.assertEqual(cmd["params"]["iso"], 400)
        self.assertEqual(cmd["params"]["shutter_speed_us"], 20000)

    def test_focus_control(self):
        cmd = json.loads(CameraControls.set_focus(distance=0.8, auto=False))
        self.assertEqual(cmd["method"], "camera.setFocus")
        self.assertFalse(cmd["params"]["auto"])
        self.assertAlmostEqual(cmd["params"]["distance"], 0.8)

    def test_thermal_saver_control(self):
        cmd = json.loads(CameraControls.set_thermal_saver(True))
        self.assertEqual(cmd["method"], "camera.setThermalSaver")
        self.assertTrue(cmd["params"]["enabled"])


class TestSignalingGatekeeper(unittest.TestCase):
    def test_gatekeeper_approval(self):
        async def run_test():
            approved_devices = []

            async def mock_approval_callback(device_info):
                approved_devices.append(device_info.get("device_name"))
                return True  # User clicks Accept

            server = SignalingServer(approval_callback=mock_approval_callback, require_approval=True)

            responses = []
            async def mock_send(resp_str):
                responses.append(json.loads(resp_str))

            hello_msg = json.dumps({
                "type": "hello",
                "payload": {
                    "device_name": "Google Pixel 8 Pro",
                    "os": "Android 14",
                    "stream_profile": "4K 30fps"
                }
            })

            await server.handle_message(hello_msg, mock_send)

            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0]["type"], "hello_ack")
            self.assertEqual(responses[0]["payload"]["status"], "approved")
            self.assertIn("Google Pixel 8 Pro", approved_devices)

        asyncio.run(run_test())

    def test_gatekeeper_rejection(self):
        async def run_test():
            async def mock_reject_callback(device_info):
                return False  # User clicks Reject

            server = SignalingServer(approval_callback=mock_reject_callback, require_approval=True)

            responses = []
            async def mock_send(resp_str):
                responses.append(json.loads(resp_str))

            hello_msg = json.dumps({
                "type": "hello",
                "payload": {
                    "device_name": "Rogue Phone",
                    "os": "iOS"
                }
            })

            await server.handle_message(hello_msg, mock_send)

            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0]["type"], "reject")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
