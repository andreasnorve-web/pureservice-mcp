"""MCP tools for Pureservice dashboard statistics."""
from __future__ import annotations

from typing import Any

from ..client import PureserviceClient
from ..config import settings


async def count_tickets_by_status() -> dict[str, Any]:
    """Return ticket counts grouped by status name.

    Useful for dashboard-style summaries.
    """
    async with PureserviceClient(settings) as client:
        # First fetch all statuses so we can map IDs to names
        statuses_response = await client.get("/status/")
        statuses = statuses_response.get("statuses", [])
        id_to_name = {s["id"]: s.get("name", f"Status {s['id']}") for s in statuses}

        # Count tickets per status
        counts: dict[str, int] = {}
        async for ticket in client.list_all("/ticket/", page_size=500):
            status_id = ticket.get("statusId")
            name = id_to_name.get(status_id, "Unknown")
            counts[name] = counts.get(name, 0) + 1

        total = sum(counts.values())
        return {"total": total, "by_status": counts}


async def list_statuses() -> dict[str, Any]:
    """List all ticket statuses configured in Pureservice."""
    async with PureserviceClient(settings) as client:
        data = await client.get("/status/")
        return data
