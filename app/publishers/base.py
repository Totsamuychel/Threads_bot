"""Base publisher abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class PublishResult:
    """Result of a publishing attempt."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    published_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class BasePublisher(ABC):
    """Abstract base class for Threads publishers."""
    
    @abstractmethod
    async def publish(self, account_id: int, text: str, hashtags: list[str] = None,
                     media_urls: list[str] = None) -> PublishResult:
        """
        Publish a post to Threads.
        
        Args:
            account_id: Database ID of the account
            text: Post text content
            hashtags: List of hashtags to include
            media_urls: Optional list of media URLs to attach
            
        Returns:
            PublishResult with success status and metadata
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if publisher service is available."""
        pass
    
    @abstractmethod
    async def get_account_info(self, account_id: int) -> Optional[dict]:
        """
        Get account information from Threads.
        
        Args:
            account_id: Database ID of the account
            
        Returns:
            Account info dict or None if unavailable
        """
        pass
    
    def _format_post_text(self, text: str, hashtags: list[str] = None) -> str:
        """
        Format post text with hashtags.
        
        Args:
            text: Main post text
            hashtags: List of hashtags
            
        Returns:
            Formatted post text
        """
        if not hashtags:
            return text
        
        # Ensure hashtags start with #
        formatted_tags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
        
        # Add hashtags at the end
        return f"{text}\n\n{' '.join(formatted_tags)}"
