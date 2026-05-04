"""FastMCP server exposing Pureservice tools.

Run locally:
    pureservice-mcp                        # stdio (Claude Desktop)
    pureservice-mcp --transport http       # HTTP (Railway / Ayfie)

Set PURESERVICE_READ_ONLY=false to enable write tools.
"""
from __future__ import annotations

import argparse
import os

from fastmcp import FastMCP

from .config import settings
from .tools import statistics, tickets, users

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

# ----------------------------------------------------------------------
# Write tools (only when READ_ONLY=false)
# ----------------------------------------------------------------------
if not settings.read_only:
    mcp.tool(tickets.create_ticket)
    mcp.tool(tickets.update_ticket)
    mcp.tool(tickets.update_ticket_status)
    mcp.tool(tickets.assign_ticket)


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
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
