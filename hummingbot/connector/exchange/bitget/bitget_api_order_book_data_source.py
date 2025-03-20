import asyncio
import logging
from typing import Any, Dict, List, Optional

from hummingbot.connector.exchange.bitget import BitgetWebUtils
from hummingbot.connector.exchange.bitget.bitget_constants import CONSTANTS, REST_URLS, WS_CHANNELS
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.web_assistant.connections.data_types import WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger


class BitgetAPIOrderBookDataSource:
    _logger: Optional[HummingbotLogger] = None

    def __init__(self, trading_pairs: List[str], api_factory: Optional[WebAssistantsFactory] = None):
        self._trading_pairs = trading_pairs
        self._api_factory = api_factory or BitgetWebUtils.build_api_factory()
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    async def get_snapshot(self, trading_pair: str) -> Dict[str, Any]:
        """Get current order book snapshot for a trading pair"""
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = BitgetWebUtils.get_rest_url_for_endpoint(REST_URLS["order_book"])
        params = {
            "symbol": trading_pair,
            "limit": 100
        }
        response = await rest_assistant.get(url=url, params=params)
        return await response.json()

    async def listen_for_subscriptions(self):
        """Subscribe to order book updates via WebSocket"""
        ws: Optional[WSAssistant] = None
        try:
            ws = await self._api_factory.get_ws_assistant()
            await ws.connect(ws_url=BitgetWebUtils.get_ws_url())
            for trading_pair in self._trading_pairs:
                subscribe_request = WSJSONRequest(
                    payload={
                        "op": "subscribe",
                        "args": [{
                            "instType": "sp",
                            "channel": WS_CHANNELS["order_book"],
                            "instId": trading_pair
                        }]
                    }
                )
                await ws.send(subscribe_request)

            async for msg in ws.iter_messages():
                if msg.data is not None:
                    self._message_queue.put_nowait(msg.data)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger().error(f"Unexpected error occurred in order book data source. Error: {str(e)}")
            raise
        finally:
            if ws is not None:
                await ws.disconnect()

    async def listen_for_trades(self, ev_loop: asyncio.AbstractEventLoop, output: asyncio.Queue):
        """Listen for trade updates via WebSocket"""
        while True:
            try:
                msg = await self._message_queue.get()
                if msg["channel"] == WS_CHANNELS["trades"]:
                    trade_msg = self._parse_trade_message(msg)
                    output.put_nowait(trade_msg)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Unexpected error parsing trade message. Error: {str(e)}")

    def _parse_trade_message(self, msg: Dict[str, Any]) -> OrderBookMessage:
        """Parse trade message from WebSocket"""
        timestamp = float(msg["ts"])
        return OrderBookMessage(
            message_type=OrderBookMessageType.TRADE,
            content=msg,
            timestamp=timestamp
        )