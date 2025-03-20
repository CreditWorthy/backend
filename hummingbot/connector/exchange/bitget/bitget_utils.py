from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import OrderState
from hummingbot.core.data_type.trade_fee import TradeFeeSchema
from hummingbot.core.utils.tracking_nonce import get_tracking_nonce

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),
    taker_percent_fee_decimal=Decimal("0.0006"),
)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USDT"


class BitgetUtils:
    @staticmethod
    def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
        """Verifies if a trading pair is enabled to operate with based on its exchange information"""
        return exchange_info.get("status", None) == "online"

    @staticmethod
    def get_client_order_id(order_side: TradeType, trading_pair: str) -> str:
        """Creates a client order id for a new order"""
        side = "B" if order_side == TradeType.BUY else "S"
        return f"{side}-{trading_pair}-{get_tracking_nonce()}"

    @staticmethod
    def convert_from_exchange_trading_pair(exchange_trading_pair: str) -> str:
        """Convert an exchange trading pair to a standard format"""
        base, quote = exchange_trading_pair.split("-")
        return f"{base}-{quote}"

    @staticmethod
    def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
        """Convert a standard format trading pair to exchange format"""
        base, quote = hb_trading_pair.split("-")
        return f"{base}-{quote}"

    @staticmethod
    def get_exchange_order_id(order_response: Dict[str, Any]) -> str:
        """Extract order id from an order response"""
        return str(order_response["orderId"])

    @staticmethod
    def convert_order_type(order_type: OrderType) -> str:
        """Convert order type to exchange format"""
        order_type_map = {
            OrderType.LIMIT: "limit",
            OrderType.MARKET: "market",
        }
        return order_type_map[order_type]

    @staticmethod
    def convert_order_side(trade_type: TradeType) -> str:
        """Convert trade type to exchange format"""
        if trade_type == TradeType.BUY:
            return "buy"
        else:
            return "sell"

    @staticmethod
    def convert_trading_rule_price_source(price_source: str) -> str:
        """Convert price source to exchange format"""
        return price_source.lower()

    @staticmethod
    def convert_decimal_to_string(value: Decimal) -> str:
        """Convert decimal to string format"""
        return f"{value:f}"

    @staticmethod
    def convert_to_exchange_order_type(order_type: OrderType) -> str:
        """Convert order type to exchange format"""
        if order_type == OrderType.LIMIT:
            return "limit"
        elif order_type == OrderType.MARKET:
            return "market"
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

class BitgetConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="bitget_perpetual", client_data=None)
    bitget_perpetual_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    bitget_perpetual_secret_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual secret key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    bitget_perpetual_passphrase: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual passphrase",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "bitget_perpetual"


KEYS = BitgetConfigMap.construct()