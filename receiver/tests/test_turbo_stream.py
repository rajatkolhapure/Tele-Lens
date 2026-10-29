"""
Tests for TeleLens Turbo Frame Pipe (Direct USB Transport).
"""

import asyncio
import struct
import unittest
import numpy as np

from telelens.stream.turbo_server import TurboStreamServer, MAGIC_HEADER, HEADER_FORMAT


class TestTurboStreamServer(unittest.TestCase):
    def test_turbo_server_packet_handling(self):
        async def run_test():
            received_frames = []

            def on_frame(frame: np.ndarray):
                received_frames.append(frame)

            server = TurboStreamServer(
                host="127.0.0.1",
                port=18991,
                on_frame=on_frame,
            )
            await server.start()

            reader, writer = await asyncio.open_connection("127.0.0.1", 18991)

            # Construct mock raw RGB frame (10x10)
            w, h = 10, 10
            raw_rgb = np.zeros((h, w, 3), dtype=np.uint8)
            raw_rgb[:, :] = [255, 128, 64]
            payload = raw_rgb.tobytes()

            header = struct.pack(
                HEADER_FORMAT,
                MAGIC_HEADER,
                len(payload),
                w,
                h,
                2,  # raw RGB format
                0,  # flags
                123456789,  # timestamp
            )

            writer.write(header + payload)
            await writer.drain()

            # Allow server time to read and process
            await asyncio.sleep(0.1)

            writer.close()
            await writer.wait_closed()
            await server.stop()

            self.assertEqual(len(received_frames), 1)
            self.assertEqual(received_frames[0].shape, (10, 10, 3))
            self.assertEqual(received_frames[0][0, 0, 0], 255)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
