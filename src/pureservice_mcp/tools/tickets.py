"""MCP tools for Pureservice tickets."""
from __future__ import annotations

from typing import Any

from ..client import PureserviceClient
from ..config import settings


async def list_tickets(
    filter_expr: str | None = None,
    sort: str | None = "modified desc",
    include: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List tickets with optional filtering and sorting.

    Args:
        filter_expr: Pureservice filter expression, e.g.
            'status.name == "Open"' or 'priorityId == 3 AND assignedUserId == 42'
        sort: Sort field with direction, e.g. "created desc" or "subject asc"
        include: Comma-separated related entities to include, e.g. "status,user"
        limit: Maximum number of tickets to return (default 50, max 500 per page)
    """
    async with PureserviceClient(settings) as client:
        results = []
        async for ticket in client.list_all(
            "/ticket/",
            filter_expr=filter_expr,
            sort=sort,
            include=include,
            max_items=limit,
        ):
            results.append(ticket)
        return {"count": len(results), "tickets": results}


async def get_ticket(ticket_id: int, include: str | None = None) -> dict[str, Any]:
    """Fetch a single ticket by ID.

    Args:
        ticket_id: The numeric ticket ID
        include: Optional related entities (e.g. "status,user,assignedUser")
    """
    async with PureserviceClient(settings) as client:
        params: dict[str, Any] = {}
        if include:
            params["include"] = include
        return await client.get(f"/ticket/{ticket_id}", **params)


async def search_tickets(query: str, limit: int = 25) -> dict[str, Any]:
    """Search tickets by text in subject (uses Contains operator).

    Args:
        query: Free-text search term matched against ticket subject
        limit: Max results to return
    """
    filter_expr = f'subject.Contains("{query}")'
    return await list_tickets(filter_expr=filter_expr, limit=limit)


# ----------------------------------------------------------------------
# Write operations
# ----------------------------------------------------------------------
async def create_ticket(
    subject: str,
    description: str,
    user_id: int | None = None,
    status_id: int | None = None,
    priority_id: int | None = None,
    assigned_user_id: int | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new ticket.

    Args:
        subject: Ticket subject line
        description: Ticket body / problem description
        user_id: ID of the requester (end user). Required by most installs.
        status_id: Initial status ID (omit to use default 'Open')
        priority_id: Priority ID (1=Low ... typically 4=Critical, varies per install)
        assigned_user_id: Agent to assign the ticket to
        extra_fields: Any other ticket fields the caller wants to set

    Returns:
        The created ticket as returned by the API.
    """
    ticket: dict[str, Any] = {
        "subject": subject,
        "description": description,
    }
    if user_id is not None:
        ticket["userId"] = user_id
    if status_id is not None:
        ticket["statusId"] = status_id
    if priority_id is not None:
        ticket["priorityId"] = priority_id
    if assigned_user_id is not None:
        ticket["assignedUserId"] = assigned_user_id
    if extra_fields:
        ticket.update(extra_fields)

    payload = {"tickets": [ticket]}

    async with PureserviceClient(settings) as client:
        return await client.post("/ticket/", payload)


async def update_ticket(
    ticket_id: int,
    subject: str | None = None,
    description: str | None = None,
    status_id: int | None = None,
    priority_id: int | None = None,
    assigned_user_id: int | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update fields on an existing ticket (PATCH = partial update).

    Only provided fields are changed.
    """
    update: dict[str, Any] = {}
    if subject is not None:
        update["subject"] = subject
    if description is not None:
        update["description"] = description
    if status_id is not None:
        update["statusId"] = status_id
    if priority_id is not None:
        update["priorityId"] = priority_id
    if assigned_user_id is not None:
        update["assignedUserId"] = assigned_user_id
    if extra_fields:
        update.update(extra_fields)

    if not update:
        raise ValueError("No fields provided to update")

    payload = {"tickets": [update]}

    async with PureserviceClient(settings) as client:
        return await client.patch(f"/ticket/{ticket_id}", payload)


async def update_ticket_status(ticket_id: int, status_id: int) -> dict[str, Any]:
    """Convenience: change just the status of a ticket.

    Tip: call list_statuses() first to find the status_id you want.
    """
    return await update_ticket(ticket_id, status_id=status_id)


async def assign_ticket(ticket_id: int, agent_user_id: int) -> dict[str, Any]:
    """Convenience: assign a ticket to an agent."""
    return await update_ticket(ticket_id, assigned_user_id=agent_user_id)

