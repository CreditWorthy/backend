from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

CONSTANTS = {
    "spot_api_url": "https://api.bitget.com",
    "spot_ws_url": "wss://ws.bitget.com/spot/v1/stream",
    "spot_api_version": "v1",
    "max_order_age": 86400.0,  # 24 hours in seconds
    "default_domain": "bitget_spot",
}

REST_URLS = {
    "auth": "/api/spot/v1/account/getInfo",
    "ping": "/api/spot/v1/public/time",
    "order_book": "/api/spot/v1/market/depth",
    "ticker": "/api/spot/v1/market/ticker",
    "symbols": "/api/spot/v1/public/products",
    "balance": "/api/spot/v1/account/assets",
    "order": "/api/spot/v1/trade/orders",
    "cancel_order": "/api/spot/v1/trade/cancel-order",
    "order_status": "/api/spot/v1/trade/order-info",
    "user_trades": "/api/spot/v1/trade/fills",
    "get_listen_key": "/api/spot/v1/user/listen-key",
    "extend_listen_key": "/api/spot/v1/user/extend-listen-key",
}

WS_CHANNELS = {
    "order_book": "depth",
    "trades": "trade",
    "ticker": "ticker",
    "user_data": "private",
}

WS_HEARTBEAT_TIME_INTERVAL = 30.0

# Rate Limits
RATE_LIMITS = [
    # Pool Configurations
    RateLimit(limit_id="spot_api", limit=20, time_interval=1),
    RateLimit(limit_id="spot_api_trading", limit=10, time_interval=1),
    RateLimit(limit_id="spot_api_trading_cancel", limit=20, time_interval=1),
    # API endpoints
    RateLimit(limit_id="get_order_book", limit=20, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api")]),
    RateLimit(limit_id="get_ticker", limit=20, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api")]),
    RateLimit(limit_id="get_symbols", limit=20, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api")]),
    RateLimit(limit_id="get_balance", limit=10, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api_trading")]),
    RateLimit(limit_id="create_order", limit=10, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api_trading")]),
    RateLimit(limit_id="cancel_order", limit=20, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api_trading_cancel")]),
    RateLimit(limit_id="get_order_status", limit=10, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api_trading")]),
    RateLimit(limit_id="get_trades", limit=10, time_interval=1,
             linked_limits=[LinkedLimitWeightPair("spot_api_trading")]),
]

# Order States
ORDER_STATE = {
    "new": OrderState.PENDING_CREATE,
    "filled": OrderState.FILLED,
    "partially_filled": OrderState.PARTIALLY_FILLED,
    "canceled": OrderState.CANCELED,
    "rejected": OrderState.FAILED,
}