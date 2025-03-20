from typing import Callable, Optional

from hummingbot.connector.exchange.bitget.bitget_constants import CONSTANTS, REST_URLS
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.connector.utils import TimeSynchronizerRESTPreProcessor
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


def public_rest_url(path_url: str, domain: str = "") -> str:
    """Creates a full URL for REST endpoints
    :param path_url: a public REST endpoint
    :param domain: the Bitget domain to connect to, defaults to default_domain from constants
    :return: the full URL to the endpoint
    """
    domain = domain or CONSTANTS["default_domain"]
    base_url = CONSTANTS["spot_api_url"]
    return base_url + path_url


def private_rest_url(path_url: str, domain: str = "") -> str:
    """Creates a full URL for REST endpoints
    :param path_url: a private REST endpoint
    :param domain: the Bitget domain to connect to, defaults to default_domain from constants
    :return: the full URL to the endpoint
    """
    return public_rest_url(path_url, domain)


def build_api_factory(
        throttler: Optional[AsyncThrottler] = None,
        time_synchronizer: Optional[TimeSynchronizer] = None,
        time_provider: Optional[Callable] = None,
        auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    """Builds the web assistants factory with throttling and time synchronization"""
    throttler = throttler or create_throttler()
    time_synchronizer = time_synchronizer or TimeSynchronizer()
    time_provider = time_provider or (lambda: get_current_server_time(throttler=throttler))
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        auth=auth,
        rest_pre_processors=[
            TimeSynchronizerRESTPreProcessor(synchronizer=time_synchronizer, time_provider=time_provider),
        ])
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(throttler: AsyncThrottler) -> WebAssistantsFactory:
    """Builds a basic web assistants factory without time synchronization"""
    api_factory = WebAssistantsFactory(throttler=throttler)
    return api_factory


def create_throttler() -> AsyncThrottler:
    """Creates an API throttler with rate limits"""
    return AsyncThrottler(CONSTANTS["RATE_LIMITS"])


async def get_current_server_time(
        throttler: Optional[AsyncThrottler] = None,
        domain: str = ""
) -> float:
    """Gets current server time from Bitget"""
    throttler = throttler or create_throttler()
    api_factory = build_api_factory_without_time_synchronizer_pre_processor(throttler=throttler)
    rest_assistant = await api_factory.get_rest_assistant()
    response = await rest_assistant.execute_request(
        url=public_rest_url(path_url=CONSTANTS["SERVER_TIME_PATH_URL"], domain=domain),
        method=RESTMethod.GET,
        throttler_limit_id=CONSTANTS["SERVER_TIME_PATH_URL"],
    )
    server_time = float(response["data"]["serverTime"])
    return server_time