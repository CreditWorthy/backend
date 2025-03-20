import base64
import hashlib
import hmac
import time
from typing import Dict, Optional

from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest


class BitgetAuth(AuthBase):
    """
    Auth class required by Bitget API
    """
    def __init__(self, api_key: str, secret_key: str, passphrase: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def _generate_signature(self, timestamp: str, method: str, path_url: str, body: str = "") -> str:
        # Ensure all parameters are strings and handle None values
        timestamp = str(timestamp) if timestamp is not None else ""
        method = str(method).upper() if method is not None else ""
        path_url = str(path_url) if path_url is not None else ""
        body = str(body) if body is not None else ""
        
        message = timestamp + method + path_url + body
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode()
        return signature

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Adds the server time and the signature to the request, required by authenticated REST calls
        """
        timestamp = str(int(time.time() * 1000))
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        request.headers = headers
        signature = self._generate_signature(
            timestamp=timestamp,
            method=request.method,
            path_url=request.url.split('com')[-1],
            body=str(request.data) if request.data is not None else ""
        )
        headers["ACCESS-SIGN"] = signature
        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to authenticate the user
        :param request: the request to add the authentication info to
        """
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(
            timestamp=timestamp,
            method="GET",
            path_url="/user/verify"
        )

        request.payload["args"] = [{
            "apiKey": self.api_key,
            "passphrase": self.passphrase,
            "timestamp": timestamp,
            "sign": signature
        }]

        return request