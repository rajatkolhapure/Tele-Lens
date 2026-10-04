"""
TeleLens Signaling Server & Approval Gatekeeper.
WebSocket server managing client handshake, laptop user approval, and WebRTC SDP/ICE exchange.
"""

import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

ApprovalCallback = Callable[[Dict[str, Any]], Awaitable[bool]]


class SignalingServer:
    """Async WebSocket signaling server with laptop approval gatekeeper."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8990,
        approval_callback: Optional[ApprovalCallback] = None,
        require_approval: bool = True
    ):
        self.host = host
        self.port = port
        self.approval_callback = approval_callback
        self.require_approval = require_approval
        self._server = None
        self._active_peer = None
        self._on_offer_callback = None
        self._on_candidate_callback = None
        self._on_disconnect_callback = None
        self._is_running = False

    def set_offer_handler(self, callback: Callable[[str, str], Awaitable[str]]) -> None:
        """callback(sdp_type, sdp_string) -> returns answer sdp string"""
        self._on_offer_callback = callback

    def set_candidate_handler(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        self._on_candidate_callback = callback

    def set_disconnect_handler(self, callback: Callable[[], None]) -> None:
        self._on_disconnect_callback = callback

    async def handle_message(self, raw_message: str, send_response: Callable[[str], Awaitable[None]]) -> None:
        """Parses and handles a single signaling message."""
        try:
            msg = json.loads(raw_message)
        except Exception as e:
            logger.error("Failed to parse signaling message JSON: %s", e)
            await send_response(json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "hello":
            # Incoming phone connection handshake
            device_name = payload.get("device_name", "Unknown Phone")
            device_os = payload.get("os", "Android/iOS")
            stream_profile = payload.get("stream_profile", "4K 30fps")

            logger.info("Incoming connection request from %s (%s, %s)", device_name, device_os, stream_profile)

            # Gatekeeper approval check
            approved = True
            if self.require_approval and self.approval_callback is not None:
                approved = await self.approval_callback(payload)

            if approved:
                logger.info("Device %s was APPROVED by laptop user.", device_name)
                await send_response(json.dumps({
                    "type": "hello_ack",
                    "payload": {
                        "status": "approved",
                        "server": "TeleLens Studio Receiver"
                    }
                }))
            else:
                logger.warning("Device %s was REJECTED by laptop user.", device_name)
                await send_response(json.dumps({
                    "type": "reject",
                    "payload": {
                        "reason": "Connection rejected by laptop user."
                    }
                }))

        elif msg_type == "offer":
            sdp = payload.get("sdp")
            sdp_type = payload.get("type", "offer")
            if self._on_offer_callback:
                answer_sdp = await self._on_offer_callback(sdp_type, sdp)
                await send_response(json.dumps({
                    "type": "answer",
                    "payload": {
                        "type": "answer",
                        "sdp": answer_sdp
                    }
                }))

        elif msg_type == "candidate":
            if self._on_candidate_callback:
                await self._on_candidate_callback(payload)

        elif msg_type == "disconnect":
            logger.info("Client signaled disconnect.")
            if self._on_disconnect_callback:
                self._on_disconnect_callback()

    async def start(self) -> None:
        """Starts the aiohttp/websockets server."""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp not installed. Please install aiohttp.")
            return

        app = web.Application()

        async def websocket_handler(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            self._is_running = True
            logger.info("Phone connected to WebSocket signaling channel.")

            async def send_fn(resp_str: str):
                await ws.send_str(resp_str)

            try:
                async for msg in ws:
                    if msg.type == web.WSMsgType.TEXT:
                        await self.handle_message(msg.data, send_fn)
                    elif msg.type == web.WSMsgType.ERROR:
                        logger.error("WebSocket error: %s", ws.exception())
            finally:
                logger.info("Phone disconnected from WebSocket signaling channel.")
                if self._on_disconnect_callback:
                    self._on_disconnect_callback()

            return ws

        app.router.add_get("/ws", websocket_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info("TeleLens Signaling Server listening on http://%s:%d/ws", self.host, self.port)
