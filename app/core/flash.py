"""Session-based flash messages (set on one request, shown on the next)."""

from typing import TypedDict

from starlette.requests import Request

FLASH_SESSION_KEY = "_flashes"


class Flash(TypedDict):
    message: str
    category: str


def flash(request: Request, message: str, category: str = "info") -> None:
    """Queue a message to display after the next page render.

    Categories map to Bootstrap alert styles: success, danger, info, warning.
    """
    flashes: list[Flash] = request.session.get(FLASH_SESSION_KEY, [])
    flashes.append({"message": message, "category": category})
    request.session[FLASH_SESSION_KEY] = flashes


def get_flashed_messages(request: Request) -> list[Flash]:
    """Pop and return all queued flash messages."""
    return request.session.pop(FLASH_SESSION_KEY, [])
