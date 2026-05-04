"""MCP tools for Pureservice users."""
from __future__ import annotations

from typing import Any

from ..client import PureserviceClient
from ..config import settings


async def list_users(
    filter_expr: str | None = None,
    role: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List users.

    Args:
        filter_expr: Optional filter expression
        role: Filter by role (10=Enduser, 20=Agent, 30=Administrator)
        limit: Max users to return
    """
    expr = filter_expr
    if role is not None:
        role_filter = f"role == {role}"
        expr = f"({filter_expr}) AND {role_filter}" if filter_expr else role_filter

    async with PureserviceClient(settings) as client:
        results = []
        async for user in client.list_all("/user/", filter_expr=expr, max_items=limit):
            results.append(user)
        return {"count": len(results), "users": results}


async def get_user(user_id: int) -> dict[str, Any]:
    """Fetch a single user by ID."""
    async with PureserviceClient(settings) as client:
        return await client.get(f"/user/{user_id}")
