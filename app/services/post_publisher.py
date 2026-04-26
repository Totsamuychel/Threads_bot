"""Post publishing service."""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Post, ActivityLog
from app.models.content import PostStatus
from app.publishers import get_publisher
from app.config import settings

logger = logging.getLogger(__name__)


class PostPublisher:
    """Service for publishing posts to Threads."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.publisher = get_publisher()
    
    async def publish_post(self, post_id: int) -> bool:
        """
        Publish a post to Threads.
        
        Args:
            post_id: Post ID to publish
            
        Returns:
            True if successful, False otherwise
        """
        # Get post
        result = await self.db.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            logger.error(f"Post {post_id} not found")
            return False
        
        # Check if already published
        if post.status == PostStatus.POSTED:
            logger.warning(f"Post {post_id} already published")
            return True
        
        # Update status
        post.status = PostStatus.PUBLISHING
        await self.db.commit()
        
        try:
            logger.info(f"Publishing post {post_id} for account {post.account_id}")
            
            # Publish via publisher
            result = await self.publisher.publish(
                account_id=post.account_id,
                text=post.text,
                hashtags=post.hashtags,
                media_urls=post.media_urls
            )
            
            if result.success:
                # Update post with success
                post.status = PostStatus.POSTED
                post.published_at = result.published_at or datetime.utcnow()
                post.threads_post_id = result.post_id
                post.threads_post_url = result.post_url
                post.last_error = None
                
                # Log success
                await self._log_activity(
                    account_id=post.account_id,
                    event_type="post_published",
                    event_category="publisher",
                    message=f"Successfully published post {post_id}",
                    post_id=post_id,
                    metadata=result.metadata
                )
                
                await self.db.commit()
                logger.info(f"Successfully published post {post_id}")
                return True
            else:
                # Update post with failure
                post.status = PostStatus.FAILED
                post.last_error = result.error
                post.retry_count += 1
                
                # Log failure
                await self._log_activity(
                    account_id=post.account_id,
                    event_type="post_failed",
                    event_category="publisher",
                    message=f"Failed to publish post {post_id}",
                    post_id=post_id,
                    error_details=result.error
                )
                
                await self.db.commit()
                logger.error(f"Failed to publish post {post_id}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {str(e)}")
            
            post.status = PostStatus.FAILED
            post.last_error = str(e)
            post.retry_count += 1
            
            await self._log_activity(
                account_id=post.account_id,
                event_type="post_error",
                event_category="publisher",
                message=f"Error publishing post {post_id}",
                post_id=post_id,
                error_details=str(e)
            )
            
            await self.db.commit()
            return False
    
    async def retry_failed_post(self, post_id: int) -> bool:
        """
        Retry publishing a failed post.
        
        Args:
            post_id: Post ID to retry
            
        Returns:
            True if successful, False otherwise
        """
        # Get post
        result = await self.db.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            logger.error(f"Post {post_id} not found")
            return False
        
        # Check retry limit
        if post.retry_count >= settings.max_retries:
            logger.warning(f"Post {post_id} exceeded max retries ({settings.max_retries})")
            return False
        
        # Reset status and retry
        post.status = PostStatus.GENERATED
        await self.db.commit()
        
        return await self.publish_post(post_id)
    
    async def _log_activity(self, account_id: int, event_type: str, event_category: str,
                           message: str, post_id: Optional[int] = None,
                           content_plan_id: Optional[int] = None,
                           metadata: Optional[dict] = None,
                           error_details: Optional[str] = None):
        """Log activity to database."""
        log = ActivityLog(
            account_id=account_id,
            event_type=event_type,
            event_category=event_category,
            message=message,
            post_id=post_id,
            content_plan_id=content_plan_id,
            event_metadata=metadata,
            error_details=error_details
        )
        
        self.db.add(log)
