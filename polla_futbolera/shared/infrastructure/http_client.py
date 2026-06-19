import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_RETRYABLE = (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)


class BaseHTTPClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: int = 30):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def _get_headers(self) -> dict:
        return {}

    def get(self, endpoint: str, params: dict | None = None, retries: int = 3) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params, headers=self._get_headers())
                    response.raise_for_status()
                    return response.json()
            except _RETRYABLE as exc:
                last_exc = exc
                wait = 2 ** attempt  # 1 s, 2 s, 4 s
                logger.warning("HTTP GET %s intento %d/%d falló (%s) — reintentando en %ds",
                               url, attempt + 1, retries, exc, wait)
                time.sleep(wait)
        raise last_exc  # type: ignore[misc]
