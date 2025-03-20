import asyncio
import logging
from typing import Optional

from hummingbot.connector.exchange.bitget import BitgetAuth
from hummingbot.connector.exchange.bitget.bitget_auth import BitgetAuth
from hummingbot.connector.exchange.bitget.bitget_constants import WS_CHANNELS
from hummingbot.connector.exchange.bitget.bitget_web_utils import BitgetWebUtils
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger


class BitgetAPIUserStreamDataSource(UserStreamTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(self, auth: BitgetAuth, api_factory: Optional[WebAssistantsFactory] = None):
        super().__init__()
        self._auth: BitgetAuth = auth
        self._api_factory = api_factory or BitgetWebUtils.build_api_factory(auth)
        self._ws_assistant: Optional[WSAssistant] = None
        self._last_ws_message_sent_timestamp = 0

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    async def _subscribe_channels(self, websocket_assistant: WSAssistant):
        """Subscribe to private channels"""
        try:
            payload = {
                "op": "subscribe",
                "args": [{
                    "instType": "sp",
                    "channel": WS_CHANNELS["user_data"],
                    "instId": "default"
                }]
            }
            subscribe_request = WSJSONRequest(payload=payload)
            await websocket_assistant.send(subscribe_request)

            self.logger().info("Subscribed to private channels...")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger().error(f"Error occurred subscribing to private channels: {str(e)}")
            raise

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """Get a connected WebSocket assistant"""
        if self._ws_assistant is None:
            self._ws_assistant = await self._api_factory.get_ws_assistant()
            await self._ws_assistant.connect(ws_url=BitgetWebUtils.get_ws_url())
            await self._subscribe_channels(self._ws_assistant)
        return self._ws_assistant

    async def _process_websocket_messages(self, websocket_assistant: WSAssistant, queue: asyncio.Queue):
        """Process incoming WebSocket messages"""
        async for ws_response in websocket_assistant.iter_messages():
            data = ws_response.data
            if data is not None:
                queue.put_nowait(data)

    async def listen_for_user_stream(self, output: asyncio.Queue):
        """Listen to user stream messages"""
        while True:
            try:
                ws: WSAssistant = await self._connected_websocket_assistant()
                await self._process_websocket_messages(ws, output)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Unexpected error while listening to user stream: {str(e)}")
                await self._sleep(5.0)
            finally:
                await self._on_user_stream_interruption(ws)

    async def _on_user_stream_interruption(self, websocket_assistant: Optional[WSAssistant] = None):
        """Handle user stream interruption"""
        self._ws_assistant = None
        await super()._on_user_stream_interruption(websocket_assistant)