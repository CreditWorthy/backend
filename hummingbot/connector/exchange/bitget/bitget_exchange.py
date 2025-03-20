import asyncio
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from hummingbot.connector.exchange.bitget import BitgetAPIOrderBookDataSource, BitgetAPIUserStreamDataSource
from hummingbot.connector.exchange.bitget.bitget_auth import BitgetAuth
from hummingbot.connector.exchange.bitget.bitget_constants import CONSTANTS, ORDER_STATE, REST_URLS
from hummingbot.connector.exchange.bitget.bitget_utils import BitgetUtils
from hummingbot.connector.exchange.bitget.bitget_web_utils import BitgetWebUtils as web_utils
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import AddedToCostTradeFee, TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.tracking_nonce import get_tracking_nonce
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class BitgetExchange(ExchangePyBase):
    web_utils = web_utils
    
    def __init__(self,
                 client_config_map: "ClientConfigAdapter",
                 bitget_api_key: str,
                 bitget_secret_key: str,
                 bitget_passphrase: str,
                 trading_pairs: Optional[List[str]] = None,
                 trading_required: bool = True):
        self._bitget_api_key = bitget_api_key
        self._bitget_secret_key = bitget_secret_key
        self._bitget_passphrase = bitget_passphrase
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        
        super().__init__(client_config_map)

    @property
    def authenticator(self):
        return BitgetAuth(
            api_key=self._bitget_api_key,
            secret_key=self._bitget_secret_key,
            passphrase=self._bitget_passphrase)
    
    @property
    def name(self) -> str:
        return "bitget"
    
    @property
    def rate_limits_rules(self):
        return CONSTANTS["RATE_LIMITS"]
    
    @property
    def domain(self):
        return CONSTANTS["default_domain"]
    
    @property
    def client_order_id_max_length(self):
        return 32  # Bitget doesn't specify a max length, using a safe value
    
    @property
    def client_order_id_prefix(self):
        return "hbot"
    
    @property
    def trading_rules_request_path(self):
        return REST_URLS["symbols"]
    
    @property
    def trading_pairs_request_path(self):
        return REST_URLS["symbols"]
    
    @property
    def check_network_request_path(self):
        return REST_URLS["ping"]
    
    @property
    def trading_pairs(self):
        return self._trading_pairs
    
    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True
    
    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]
    
    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        # Implement based on Bitget API error responses related to time synchronization
        error_description = str(request_exception)
        return "timestamp" in error_description.lower() and "invalid" in error_description.lower()
    
    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        # Implement based on Bitget API error responses for order not found
        error_description = str(status_update_exception)
        return "order not found" in error_description.lower()
    
    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        # Implement based on Bitget API error responses for order not found during cancellation
        error_description = str(cancelation_exception)
        return "order not found" in error_description.lower()
    
    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            auth=self._auth)
    
    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return BitgetAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory)
    
    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return BitgetAPIUserStreamDataSource(
            auth=self._auth,
            connector=self,
            api_factory=self._web_assistants_factory)

    async def _place_order(self,
                           order_id: str,
                           trading_pair: str,
                           amount: Decimal,
                           trade_type: TradeType,
                           order_type: OrderType,
                           price: Decimal,
                           **kwargs) -> Tuple[str, float]:
        
        data = {
            "symbol": BitgetUtils.convert_to_exchange_trading_pair(trading_pair),
            "side": BitgetUtils.convert_order_side(trade_type),
            "orderType": BitgetUtils.convert_order_type(order_type),
            "size": str(amount),
            "clientOrderId": order_id
        }
        
        if order_type is not OrderType.MARKET:
            data["price"] = str(price)
            
        response = await self._api_post(
            path_url=REST_URLS["order"],
            data=data,
            is_auth_required=True)
            
        exchange_order_id = BitgetUtils.get_exchange_order_id(response)
        return exchange_order_id, self.current_timestamp

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        data = {
            "symbol": BitgetUtils.convert_to_exchange_trading_pair(tracked_order.trading_pair),
            "orderId": tracked_order.exchange_order_id
        }
        
        try:
            response = await self._api_post(
                path_url=REST_URLS["cancel_order"],
                data=data,
                is_auth_required=True)
                
            return response.get("code") == "00000"
        except Exception as e:
            self.logger().error(f"Failed to cancel order {order_id}: {str(e)}")
            return False

    async def get_order_status(self, order_id: str) -> OrderState:
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = BitgetWebUtils.get_rest_url_for_endpoint(REST_URLS["order_status"])
        params = {"orderId": order_id}
        response = await rest_assistant.get(url=url, params=params)
        response_data = await response.json()
        return ORDER_STATE[response_data["status"]]

    async def get_order_price(self, order_id: str) -> Decimal:
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = BitgetWebUtils.get_rest_url_for_endpoint(REST_URLS["order_status"])
        params = {"orderId": order_id}
        response = await rest_assistant.get(url=url, params=params)
        response_data = await response.json()
        return Decimal(response_data["price"])

    async def get_order_update_for_order(self, order: InFlightOrder) -> OrderUpdate:
        current_state = await self.get_order_status(order.exchange_order_id)
        current_price = await self.get_order_price(order.exchange_order_id)
        return OrderUpdate(
            client_order_id=order.client_order_id,
            exchange_order_id=order.exchange_order_id,
            trading_pair=order.trading_pair,
            update_timestamp=int(time.time() * 1e3),
            new_state=current_state,
            client_order_id_for_contingency=order.client_order_id_for_contingency,
        )

    async def get_all_balances(self) -> Dict[str, Decimal]:
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = BitgetWebUtils.get_rest_url_for_endpoint(REST_URLS["balance"])
        response = await rest_assistant.get(url=url)
        response_data = await response.json()
        return {asset["coinName"]: Decimal(asset["available"]) for asset in response_data["data"]}

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    def _get_fee(self,
                 base_currency: str,
                 quote_currency: str,
                 order_type: OrderType,
                 order_side: TradeType,
                 amount: Decimal,
                 price: Decimal = s_decimal_NaN,
                 is_maker: Optional[bool] = None) -> TradeFeeBase:
        is_maker = is_maker or (order_type is OrderType.LIMIT_MAKER)
        fee = Decimal("0.001") if is_maker else Decimal("0.002")
        return AddedToCostTradeFee(percent=fee)