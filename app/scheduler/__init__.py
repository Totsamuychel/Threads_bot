"""Scheduler initialization and configuration."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.scheduler.tasks import (
    generate_content_plans,
    generate_posts_for_upcoming,
    publish_scheduled_posts,
    retry_failed_posts,
    cleanup_old_logs,
    run_social_actions,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and configure the scheduler."""
    global scheduler
    
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled in settings")
        return None
    
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    
    # Content plan generation - daily at 1 AM
    scheduler.add_job(
        generate_content_plans,
        trigger=CronTrigger(hour=1, minute=0),
        id="generate_content_plans",
        name="Generate content plans for all accounts",
        replace_existing=True
    )
    
    # Post generation - every hour
    scheduler.add_job(
        generate_posts_for_upcoming,
        trigger=IntervalTrigger(hours=1),
        id="generate_posts",
        name="Generate posts for upcoming plans",
        replace_existing=True
    )
    
    # Post publishing - every minute
    scheduler.add_job(
        publish_scheduled_posts,
        trigger=IntervalTrigger(minutes=1),
        id="publish_posts",
        name="Publish scheduled posts",
        replace_existing=True
    )
    
    # Retry failed posts - every 5 minutes
    scheduler.add_job(
        retry_failed_posts,
        trigger=IntervalTrigger(minutes=5),
        id="retry_failed_posts",
        name="Retry failed posts",
        replace_existing=True
    )
    
    # Social actions (likes, replies, follows) - every 3 hours
    scheduler.add_job(
        run_social_actions,
        trigger=IntervalTrigger(hours=3),
        id="social_actions",
        name="Perform social interactions (likes/replies/follows)",
        replace_existing=True
    )

    # Cleanup old logs - daily at 3 AM
    scheduler.add_job(
        cleanup_old_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_logs",
        name="Clean up old activity logs",
        replace_existing=True
    )
    
    logger.info("Scheduler initialized with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id})")
    
    return scheduler


def start_scheduler():
    """Start the scheduler."""
    global scheduler
    
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


__all__ = ["init_scheduler", "start_scheduler", "shutdown_scheduler", "scheduler"]
