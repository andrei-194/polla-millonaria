import httpx
from typing import Any


class BaseHTTPClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: int = 30):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def _get_headers(self) -> dict:
        return {}

    def get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
