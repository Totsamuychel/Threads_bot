"""Publisher factory and exports."""

from app.publishers.base import BasePublisher, PublishResult
from app.publishers.mock import MockPublisher
from app.publishers.threads_api import ThreadsAPIPublisher
from app.config import settings
from typing import Optional


def get_publisher(publisher_type: Optional[str] = None) -> BasePublisher:
    """
    Factory function to get appropriate publisher.
    
    Args:
        publisher_type: Type of publisher (mock, api, browser). Defaults to settings.
    
    Returns:
        Configured publisher instance
    """
    publisher_type = publisher_type or settings.threads_publisher
    
    if publisher_type.lower() == "mock":
        return MockPublisher()
    elif publisher_type.lower() == "api":
        return ThreadsAPIPublisher(
            api_url=settings.threads_api_url,
            api_key=settings.threads_api_key
        )
    else:
        raise ValueError(f"Unknown publisher type: {publisher_type}")


__all__ = ["BasePublisher", "PublishResult", "MockPublisher", "ThreadsAPIPublisher", "get_publisher"]
