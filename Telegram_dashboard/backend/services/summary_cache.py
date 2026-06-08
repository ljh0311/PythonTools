import hashlib
import json
import time
from typing import Any

from backend.config import SUMMARY_CACHE_TTL


class SummaryCache:
    def __init__(self, ttl_seconds: int = SUMMARY_CACHE_TTL):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def _key(self, filters: dict[str, Any], summary_type: str) -> str:
        payload = json.dumps({"filters": filters, "summary_type": summary_type}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, filters: dict[str, Any], summary_type: str) -> dict[str, Any] | None:
        key = self._key(filters, summary_type)
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        value = dict(value)
        value["cached"] = True
        return value

    def set(self, filters: dict[str, Any], summary_type: str, value: dict[str, Any]) -> None:
        key = self._key(filters, summary_type)
        self._store[key] = (time.time() + self.ttl_seconds, value)

    def invalidate_all(self) -> None:
        self._store.clear()


summary_cache = SummaryCache()
