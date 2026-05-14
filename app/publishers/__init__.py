"""Publisher factory and exports."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.publishers.base import BasePublisher, PublishResult
from app.publishers.mock import MockPublisher
from app.publishers.threads_api import ThreadsAPIPublisher
from app.publishers.browser_publisher import BrowserPublisher
from app.config import settings


def get_publisher(
    publisher_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> BasePublisher:
    """Return publisher instance — account-level type takes priority over global config."""
    ptype = (publisher_type or settings.threads_publisher).lower()

    if ptype == "mock":
        return MockPublisher()
    elif ptype == "api":
        return ThreadsAPIPublisher(db=db)
    elif ptype == "browser":
        return BrowserPublisher()
    else:
        raise ValueError(f"Unknown publisher type: {ptype}")


__all__ = [
    "BasePublisher", "PublishResult", "MockPublisher",
    "ThreadsAPIPublisher", "BrowserPublisher", "get_publisher",
]
