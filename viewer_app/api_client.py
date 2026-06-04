from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class GatewayApiClient:
    base_url: str
    timeout_seconds: float = 2.5

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def fetch_state(self) -> dict[str, Any]:
        response = requests.get(self._url("/api/state"), timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        state = payload.get("state")
        if isinstance(state, dict):
            merged = dict(payload)
            merged.update(state)
            merged.pop("state", None)
            return merged
        return payload
