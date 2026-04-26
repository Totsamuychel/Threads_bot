"""Mock publisher for development and testing."""

import logging
from typing import Optional
from datetime import datetime, timezone
from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)


class MockPublisher(BasePublisher):
    """Mock publisher that simulates posting without actually publishing."""
    
    def __init__(self):
        self.published_posts = []
    
    async def publish(self, account_id: int, text: str, hashtags: list[str] = None,
                     media_urls: list[str] = None) -> PublishResult:
        """Simulate publishing a post."""
        
        # Format the post
        formatted_text = self._format_post_text(text, hashtags)
        
        # Generate mock post ID
        post_id = f"mock_{datetime.now(timezone.utc).timestamp()}"
        post_url = f"https://threads.net/@account/post/{post_id}"
        
        # Store for inspection
        post_data = {
            "account_id": account_id,
            "text": formatted_text,
            "hashtags": hashtags,
            "media_urls": media_urls,
            "post_id": post_id,
            "post_url": post_url,
            "published_at": datetime.now(timezone.utc)
        }
        self.published_posts.append(post_data)
        
        # Log the "published" post
        logger.info(f"[MOCK PUBLISH] Account {account_id}")
        logger.info(f"Post ID: {post_id}")
        logger.info(f"Content:\n{formatted_text}")
        if media_urls:
            logger.info(f"Media: {media_urls}")
        logger.info("-" * 80)
        
        return PublishResult(
            success=True,
            post_id=post_id,
            post_url=post_url,
            published_at=datetime.now(timezone.utc),
            metadata={"mock": True}
        )
    
    async def health_check(self) -> bool:
        """Mock publisher is always available."""
        return True
    
    async def get_account_info(self, account_id: int) -> Optional[dict]:
        """Return mock account info."""
        return {
            "id": account_id,
            "username": f"mock_user_{account_id}",
            "followers": 1000,
            "following": 500,
            "posts_count": len([p for p in self.published_posts if p["account_id"] == account_id])
        }
