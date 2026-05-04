"""Smoke tests for the Pureservice client.

These use respx to mock HTTP calls so we can run them without an API key.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from pureservice_mcp.client import PureserviceClient
from pureservice_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        tenant="test",
        api_key="dummy-key",
        api_base_path="/api",
    )


@respx.mock
@pytest.mark.asyncio
async def test_get_single_ticket(settings: Settings) -> None:
    route = respx.get("https://test.pureservice.com/api/ticket/42").mock(
        return_value=httpx.Response(200, json={"tickets": [{"id": 42, "subject": "Test"}]})
    )
    async with PureserviceClient(settings) as client:
        result = await client.get("/ticket/42")

    assert route.called
    assert result["tickets"][0]["id"] == 42


@respx.mock
@pytest.mark.asyncio
async def test_auth_header_present(settings: Settings) -> None:
    route = respx.get("https://test.pureservice.com/api/status/").mock(
        return_value=httpx.Response(200, json={"statuses": []})
    )
    async with PureserviceClient(settings) as client:
        await client.get("/status/")

    assert route.calls[0].request.headers["X-Authorization-Key"] == "dummy-key"
    assert route.calls[0].request.headers["Accept"] == "application/vnd.api+json"


@respx.mock
@pytest.mark.asyncio
async def test_pagination(settings: Settings) -> None:
    # Two pages: first returns full page, second returns partial -> stop
    page1 = [{"id": i} for i in range(100)]
    page2 = [{"id": i} for i in range(100, 150)]

    respx.get("https://test.pureservice.com/api/ticket/", params={"start": 0, "limit": 100}).mock(
        return_value=httpx.Response(200, json={"tickets": page1})
    )
    respx.get("https://test.pureservice.com/api/ticket/", params={"start": 100, "limit": 100}).mock(
        return_value=httpx.Response(200, json={"tickets": page2})
    )

    async with PureserviceClient(settings) as client:
        items = [t async for t in client.list_all("/ticket/")]

    assert len(items) == 150


@respx.mock
@pytest.mark.asyncio
async def test_429_retry(settings: Settings) -> None:
    respx.get("https://test.pureservice.com/api/status/").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"statuses": [{"id": 1}]}),
        ]
    )
    async with PureserviceClient(settings) as client:
        result = await client.get("/status/")
    assert result["statuses"][0]["id"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_post_payload_format(settings: Settings) -> None:
    """Verify create_ticket sends JSON:API-style payload."""
    import json

    route = respx.post("https://test.pureservice.com/api/ticket/").mock(
        return_value=httpx.Response(200, json={"tickets": [{"id": 999, "subject": "x"}]})
    )

    async with PureserviceClient(settings) as client:
        await client.post("/ticket/", {"tickets": [{"subject": "x", "description": "y"}]})

    body = json.loads(route.calls[0].request.content)
    assert "tickets" in body
    assert body["tickets"][0]["subject"] == "x"


@respx.mock
@pytest.mark.asyncio
async def test_patch_partial_update(settings: Settings) -> None:
    route = respx.patch("https://test.pureservice.com/api/ticket/42").mock(
        return_value=httpx.Response(200, json={"tickets": [{"id": 42}]})
    )
    async with PureserviceClient(settings) as client:
        await client.patch("/ticket/42", {"tickets": [{"statusId": 5}]})
    assert route.called
