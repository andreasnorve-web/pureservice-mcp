"""FastMCP server exposing Pureservice tools.

Run locally:
    pureservice-mcp                        # stdio (Claude Desktop)
    pureservice-mcp --transport http       # HTTP (Railway / Ayfie)

Set PURESERVICE_READ_ONLY=false to enable write tools.
Set PURESERVICE_GATEWAY_TOKEN=<secret> to require X-MCP-Auth header on HTTP.
"""
from __future__ import annotations

import argparse
import hmac
import os

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .tools import departments, statistics, tickets, users

mcp: FastMCP = FastMCP(
    name="pureservice-mcp",
    instructions=(
        "Tools for the Pureservice IT service management platform. "
        "Use list_tickets to search the ticket queue, get_ticket for a single "
        "ticket by ID, and count_tickets_by_status for dashboard summaries."
    ),
)

# ----------------------------------------------------------------------
# Read tools (always available)
# ----------------------------------------------------------------------
mcp.tool(tickets.list_tickets)
mcp.tool(tickets.get_ticket)
mcp.tool(tickets.search_tickets)

mcp.tool(users.list_users)
mcp.tool(users.get_user)

mcp.tool(statistics.count_tickets_by_status)
mcp.tool(statistics.list_statuses)

# Department / zone tools
mcp.tool(departments.list_departments)
mcp.tool(departments.list_ticket_types)
mcp.tool(departments.list_request_types)
mcp.tool(departments.list_tickets_by_department)
mcp.tool(departments.list_hr_tickets)
mcp.tool(departments.list_it_tickets)
mcp.tool(departments.list_economy_tickets)
mcp.tool(departments.department_overview)

# ----------------------------------------------------------------------
# Write tools (only when READ_ONLY=false)
# ----------------------------------------------------------------------
if not settings.read_only:
    mcp.tool(tickets.create_ticket)
    mcp.tool(tickets.update_ticket)
    mcp.tool(tickets.update_ticket_status)
    mcp.tool(tickets.assign_ticket)


# ----------------------------------------------------------------------
# Gateway auth middleware (HTTP transport only)
# ----------------------------------------------------------------------
class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Require X-MCP-Auth header to match settings.gateway_token.

    If gateway_token is empty (default), no auth is enforced.
    Constant-time comparison via hmac.compare_digest avoids timing leaks.
    """

    HEADER_NAME = "x-mcp-auth"

    async def dispatch(self, request, call_next):
        if not settings.gateway_token:
            return await call_next(request)

        # Allow OPTIONS preflight without auth (CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

        provided = request.headers.get(self.HEADER_NAME, "")
        if not hmac.compare_digest(provided, settings.gateway_token):
            return JSONResponse(
                {"error": "unauthorized", "message": "Missing or invalid X-MCP-Auth header"},
                status_code=401,
            )
        return await call_next(request)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Pureservice MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport: stdio for Claude Desktop, http for Railway/Ayfie",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind when using http transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Port to bind when using http transport (Railway sets PORT)",
    )
    args = parser.parse_args()

    if args.transport == "http":
        # Attach the auth middleware to the underlying ASGI app.
        # FastMCP exposes http_app() which returns a Starlette app we can wrap.
        app = mcp.http_app()
        app.add_middleware(GatewayAuthMiddleware)

        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port)
    else:
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
