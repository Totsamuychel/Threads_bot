"""Publisher factory and exports."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.publishers.base import BasePublisher, PublishResult
from app.publishers.mock import MockPublisher
from app.publishers.threads_api import ThreadsAPIPublisher
from app.config import settings


def get_publisher(
    publisher_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> BasePublisher:
    """Return the configured publisher instance."""
    publisher_type = publisher_type or settings.threads_publisher

    if publisher_type.lower() == "mock":
        return MockPublisher()
    elif publisher_type.lower() == "api":
        return ThreadsAPIPublisher(db=db)
    else:
        raise ValueError(f"Unknown publisher type: {publisher_type}")


__all__ = ["BasePublisher", "PublishResult", "MockPublisher", "ThreadsAPIPublisher", "get_publisher"]
