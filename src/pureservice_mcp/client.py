"""HTTP client for the Pureservice REST API.

Handles:
  * Authentication via X-Authorization-Key header
  * JSON:API content negotiation
  * Rate limiting (token bucket, stays under 100 req/min)
  * Automatic retry on 429 with Retry-After
  * Pagination using start/limit
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator

import httpx

from .config import Settings


class PureserviceError(Exception):
    """Base exception for Pureservice API errors."""


class PureserviceClient:
    """Async HTTP client for Pureservice."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

        # Simple token bucket for rate limiting
        self._tokens: float = settings.requests_per_minute
        self._last_refill: float = time.monotonic()
        self._bucket_lock = asyncio.Lock()

    async def __aenter__(self) -> "PureserviceClient":
        self._client = httpx.AsyncClient(
            base_url=self.settings.base_url,
            headers={
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
                "X-Authorization-Key": self.settings.api_key,
            },
            timeout=self.settings.timeout_seconds,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    async def _acquire_token(self) -> None:
        """Wait until a request slot is available (token bucket)."""
        async with self._bucket_lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            refill = elapsed * (self.settings.requests_per_minute / 60.0)
            self._tokens = min(
                self.settings.requests_per_minute, self._tokens + refill
            )
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) * (60.0 / self.settings.requests_per_minute)
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1

    # ------------------------------------------------------------------
    # Core request method
    # ------------------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make an authenticated request and return parsed JSON."""
        if self._client is None:
            raise PureserviceError("Client not initialised. Use as async context manager.")

        for attempt in range(max_retries + 1):
            await self._acquire_token()
            response = await self._client.request(
                method, path, params=params, json=json
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", "5"))
                if attempt < max_retries:
                    await asyncio.sleep(retry_after)
                    continue
                raise PureserviceError("Rate limit exceeded after retries")

            if response.status_code >= 400:
                raise PureserviceError(
                    f"{method} {path} -> {response.status_code}: {response.text}"
                )

            if not response.content:
                return {}
            return response.json()

        raise PureserviceError("Unreachable: retries exhausted")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        return await self.request("GET", path, params=params or None)

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", path, json=payload)

    async def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PATCH", path, json=payload)

    async def delete(self, path: str) -> dict[str, Any]:
        return await self.request("DELETE", path)

    # ------------------------------------------------------------------
    # Auto-paginating list helper
    # ------------------------------------------------------------------
    async def list_all(
        self,
        path: str,
        *,
        filter_expr: str | None = None,
        sort: str | None = None,
        include: str | None = None,
        page_size: int | None = None,
        max_items: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield entities one by one, transparently paging through results."""
        size = page_size or self.settings.default_page_size
        start = 0
        yielded = 0

        while True:
            params: dict[str, Any] = {"start": start, "limit": size}
            if filter_expr:
                params["filter"] = filter_expr
            if sort:
                params["sort"] = sort
            if include:
                params["include"] = include

            data = await self.request("GET", path, params=params)

            # JSON:API style response - the entity list lives under a key
            # matching the resource name, e.g. "tickets", "statuses".
            items: list[dict[str, Any]] = []
            for value in data.values():
                if isinstance(value, list):
                    items = value
                    break

            if not items:
                return

            for item in items:
                yield item
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return

            if len(items) < size:
                return  # Last page
            start += size
