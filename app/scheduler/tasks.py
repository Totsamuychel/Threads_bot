"""Scheduled tasks for content generation and publishing."""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, delete
from app.database import AsyncSessionLocal
from app.models import Account, ContentPlan, Post, ActivityLog
from app.models.content import PostStatus
from app.services import ContentPlanner, PostGenerator, PostPublisher
from app.services.notifier import notifier
from app.config import settings

logger = logging.getLogger(__name__)


async def generate_content_plans():
    """
    Scheduled task to generate content plans for all active accounts.
    Runs daily to ensure plans exist for upcoming days.
    """
    logger.info("Running content plan generation task")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Account).where(Account.is_active == True)
            )
            accounts = result.scalars().all()
            
            planner = ContentPlanner(db)
            
            # Parallelize plan generation for all accounts
            tasks = [planner.generate_plan_for_account(account.id) for account in accounts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_created = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error generating plans for account {accounts[i].id}: {str(result)}")
                elif result:
                    total_created += len(result)
            
            logger.info(f"Content plan generation complete. Created {total_created} plans.")
            
        except Exception as e:
            logger.error(f"Error in content plan generation task: {str(e)}")


async def generate_posts_for_upcoming():
    """
    Scheduled task to generate posts for upcoming content plans.
    Runs every hour to generate content N hours before scheduled time.
    """
    logger.info("Running post generation task")
    
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            generation_window = now + timedelta(hours=settings.generation_hours_before)
            
            result = await db.execute(
                select(ContentPlan).where(
                    and_(
                        ContentPlan.status == PostStatus.PLANNED,
                        ContentPlan.scheduled_time <= generation_window,
                        ContentPlan.scheduled_time > now
                    )
                ).order_by(ContentPlan.scheduled_time)
            )
            plans = result.scalars().all()
            
            if not plans:
                logger.info("No plans need content generation")
                return
            
            logger.info(f"Found {len(plans)} plans needing content generation")
            
            generator = PostGenerator(db)
            
            generated_count = 0
            for plan in plans:
                try:
                    post = await generator.generate_post_for_plan(plan.id)
                    if post:
                        generated_count += 1
                except Exception as e:
                    logger.error(f"Error generating post for plan {plan.id}: {str(e)}")
            
            logger.info(f"Post generation complete. Generated {generated_count}/{len(plans)} posts.")
            
        except Exception as e:
            logger.error(f"Error in post generation task: {str(e)}")


async def publish_scheduled_posts():
    """
    Scheduled task to publish posts at their scheduled time.
    Runs every minute to check for posts ready to publish.
    """
    logger.info("Running post publishing task")
    
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            
            result = await db.execute(
                select(Post).where(
                    and_(
                        Post.status.in_([PostStatus.GENERATED, PostStatus.SCHEDULED]),
                        Post.scheduled_time <= now
                    )
                ).order_by(Post.scheduled_time).limit(10)
            )
            posts = result.scalars().all()
            
            if not posts:
                logger.debug("No posts ready to publish")
                return
            
            logger.info(f"Found {len(posts)} posts ready to publish")
            
            publisher = PostPublisher(db)
            
            published_count = 0
            for post in posts:
                try:
                    success = await publisher.publish_post(post.id)
                    if success:
                        published_count += 1
                    else:
                        # Fetch updated post to get error message
                        updated = await db.execute(select(Post).where(Post.id == post.id))
                        failed = updated.scalar_one_or_none()
                        error_msg = failed.last_error if failed else None
                        retry_count = failed.retry_count if failed else 0
                        await notifier.notify_post_failed(
                            post.account_id, post.id, error_msg, retry_count
                        )
                except Exception as e:
                    logger.error(f"Error publishing post {post.id}: {str(e)}")

            logger.info(f"Publishing complete. Published {published_count}/{len(posts)} posts.")
            
        except Exception as e:
            logger.error(f"Error in post publishing task: {str(e)}")


async def retry_failed_posts():
    """
    Scheduled task to retry failed posts with exponential backoff.
    Runs every 5 minutes.
    """
    logger.info("Running failed post retry task")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Post).where(
                    and_(
                        Post.status == PostStatus.FAILED,
                        Post.retry_count < settings.max_retries
                    )
                )
            )
            posts = result.scalars().all()
            
            if not posts:
                logger.debug("No failed posts to retry")
                return
            
            logger.info(f"Found {len(posts)} failed posts to retry")
            
            publisher = PostPublisher(db)
            
            retried_count = 0
            for post in posts:
                try:
                    delay_seconds = settings.retry_delay_seconds * (settings.retry_backoff_multiplier ** post.retry_count)

                    if post.updated_at:
                        time_since_update = (datetime.now(timezone.utc) - post.updated_at).total_seconds()
                        if time_since_update < delay_seconds:
                            logger.debug(f"Post {post.id} not ready for retry yet")
                            continue

                    is_last_attempt = (post.retry_count + 1 >= settings.max_retries)
                    success = await publisher.retry_failed_post(post.id)
                    if success:
                        retried_count += 1
                    elif is_last_attempt:
                        # Max retries exhausted — fetch fresh error and alert
                        updated = await db.execute(select(Post).where(Post.id == post.id))
                        exhausted = updated.scalar_one_or_none()
                        error_msg = exhausted.last_error if exhausted else None
                        await notifier.notify_post_exhausted(post.account_id, post.id, error_msg)

                except Exception as e:
                    logger.error(f"Error retrying post {post.id}: {str(e)}")

            logger.info(f"Retry complete. Successfully retried {retried_count}/{len(posts)} posts.")
            
        except Exception as e:
            logger.error(f"Error in retry task: {str(e)}")


async def cleanup_old_logs():
    """
    Scheduled task to clean up old activity logs.
    Runs daily to keep database size manageable.
    """
    logger.info("Running log cleanup task")
    
    async with AsyncSessionLocal() as db:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
            
            result = await db.execute(
                delete(ActivityLog).where(ActivityLog.created_at < cutoff_date)
            )
            deleted_count = result.rowcount
            
            await db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old log entries")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
