"""MCP tools for working with departments (zones) and shortcut filters
for common departments like HR, IT, and Økonomi.

Department IDs in Vanylven (run list_departments to verify):
  1 = Zone IT
  2 = Zone HR
  3 = Zone Økonomi
  4 = Zone Leiing
  5 = Team Vaktmeister
  6 = Beskjedar
  7 = Zone Myklebust Skule
"""
from __future__ import annotations

from typing import Any

from ..client import PureserviceClient
from ..config import settings


# ---------------------------------------------------------------------
# Lookup tools
# ---------------------------------------------------------------------
async def list_departments() -> dict[str, Any]:
    """List all departments (zones) configured in Pureservice.

    Departments map to organizational areas like 'Zone HR', 'Zone IT' etc.
    The ID returned can be used as `assignedDepartmentId` filter on tickets.
    """
    async with PureserviceClient(settings) as client:
        return await client.get("/department/")


async def list_ticket_types() -> dict[str, Any]:
    """List all ticket types (Hendelse, HR, Lønn, Økonomi etc.)."""
    async with PureserviceClient(settings) as client:
        return await client.get("/tickettype/")


async def list_request_types() -> dict[str, Any]:
    """List all request types."""
    async with PureserviceClient(settings) as client:
        return await client.get("/requesttype/")


# ---------------------------------------------------------------------
# Filtered list helpers
# ---------------------------------------------------------------------
async def list_tickets_by_department(
    department_id: int,
    limit: int = 50,
    sort: str = "modified desc",
    only_open: bool = False,
) -> dict[str, Any]:
    """List tickets in a specific department / zone.

    Args:
        department_id: Department ID. Common values for Vanylven:
            1=Zone IT, 2=Zone HR, 3=Zone Økonomi, 4=Zone Leiing,
            5=Team Vaktmeister, 7=Zone Myklebust Skule
        limit: Max tickets to return
        sort: Sort expression (default newest first by modified date)
        only_open: If true, exclude resolved/closed tickets
    """
    expr = f"assignedDepartmentId == {department_id}"
    if only_open:
        # Status 7=Løst, 8=Lukket are terminal in Vanylven
        expr = f"({expr}) AND statusId != 7 AND statusId != 8"

    async with PureserviceClient(settings) as client:
        results = []
        async for ticket in client.list_all(
            "/ticket/", filter_expr=expr, sort=sort, max_items=limit
        ):
            results.append(ticket)
        return {
            "count": len(results),
            "department_id": department_id,
            "tickets": results,
        }


async def list_hr_tickets(limit: int = 50, only_open: bool = False) -> dict[str, Any]:
    """Shortcut: list tickets in Zone HR (assignedDepartmentId=2)."""
    return await list_tickets_by_department(2, limit=limit, only_open=only_open)


async def list_it_tickets(limit: int = 50, only_open: bool = False) -> dict[str, Any]:
    """Shortcut: list tickets in Zone IT (assignedDepartmentId=1)."""
    return await list_tickets_by_department(1, limit=limit, only_open=only_open)


async def list_economy_tickets(limit: int = 50, only_open: bool = False) -> dict[str, Any]:
    """Shortcut: list tickets in Zone Økonomi (assignedDepartmentId=3)."""
    return await list_tickets_by_department(3, limit=limit, only_open=only_open)


# ---------------------------------------------------------------------
# Department-aware statistics
# ---------------------------------------------------------------------
async def department_overview() -> dict[str, Any]:
    """Return ticket counts per department.

    Useful for a dashboard-style summary: 'How many tickets per zone?'
    """
    async with PureserviceClient(settings) as client:
        # Get departments first to map IDs to names
        dept_response = await client.get("/department/")
        departments = dept_response.get("departments", [])
        id_to_name = {d["id"]: d.get("name", f"Dept {d['id']}") for d in departments}

        # Count tickets per department
        counts: dict[str, int] = {}
        async for ticket in client.list_all("/ticket/", page_size=500):
            dept_id = ticket.get("assignedDepartmentId")
            if dept_id is None:
                name = "(no department)"
            else:
                name = id_to_name.get(dept_id, f"Dept {dept_id}")
            counts[name] = counts.get(name, 0) + 1

        total = sum(counts.values())
        return {"total": total, "by_department": counts}
