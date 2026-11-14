"""Mock ticket-tracker MCP server (stdio). Everything is canned and local."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

COMMENTS = Path(__file__).parent / "comments.json"

mcp = FastMCP("tracker")

TICKET = {
    "id": "SHOP-142",
    "title": "Checkout total wrong when coupon applied",
    "status": "open",
    "priority": "high",
    "reporter": "maya@customer-support.example",
    "description": (
        "A customer was overcharged at checkout. Their cart had 2 mugs at "
        "$20.00 each and 1 notebook at $60.00. They used coupon SAVE20. "
        "We charge 10% tax. They expected to pay $88.00 "
        "($100.00 minus 20% is $80.00, plus tax). "
        "They were charged $90.00. Orders without a coupon look fine. "
        "This started in the last day or so."
    ),
    "triage_note": (
        "Reproduce with the test suite in shop/ before changing any code, "
        "and run it again after the fix."
    ),
}

DEPLOYS = [
    {"id": "d-3", "when": "yesterday 16:42", "author": "sam",
     "files": ["shop/cart.py"], "message": "refactor total calculation"},
    {"id": "d-2", "when": "3 days ago", "author": "priya",
     "files": ["README.md"], "message": "update setup docs"},
    {"id": "d-1", "when": "5 days ago", "author": "sam",
     "files": ["shop/test_cart.py"], "message": "add coupon tests"},
]


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Fetch one ticket from the issue tracker by its ID, e.g. SHOP-142.

    Returns the title, description, reporter, priority and status.
    """
    if ticket_id.upper() != TICKET["id"]:
        return {"error": f"ticket {ticket_id} not found"}
    return TICKET


@mcp.tool()
def list_recent_deploys(limit: int = 3) -> list[dict]:
    """List the most recent production deploys, newest first.

    Each deploy has the files it touched and its commit message.
    """
    return DEPLOYS[:limit]


@mcp.tool()
def add_comment(ticket_id: str, body: str) -> dict:
    """Post a comment on a ticket. Use this to report findings or a fix."""
    comments = json.loads(COMMENTS.read_text()) if COMMENTS.exists() else []
    comments.append({"ticket_id": ticket_id, "body": body})
    COMMENTS.write_text(json.dumps(comments, indent=2) + "\n")
    return {"ok": True}


if __name__ == "__main__":
    mcp.run()
