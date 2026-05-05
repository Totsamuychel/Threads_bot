"""Dashboard and analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Account, ContentPlan, Post, ActivityLog
from app.models.content import PostStatus

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    account_id: Optional[int] = None,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get posting statistics."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Base queries
    posts_query = select(Post).where(Post.created_at >= cutoff_date)
    plans_query = select(ContentPlan).where(ContentPlan.created_at >= cutoff_date)
    
    if account_id:
        posts_query = posts_query.where(Post.account_id == account_id)
        plans_query = plans_query.where(ContentPlan.account_id == account_id)
    
    # Get posts
    posts_result = await db.execute(posts_query)
    posts = posts_result.scalars().all()
    
    # Get plans
    plans_result = await db.execute(plans_query)
    plans = plans_result.scalars().all()
    
    # Calculate stats
    total_posts = len(posts)
    posted = len([p for p in posts if p.status == PostStatus.POSTED])
    failed = len([p for p in posts if p.status == PostStatus.FAILED])
    pending = len([p for p in posts if p.status in [PostStatus.GENERATED, PostStatus.SCHEDULED]])
    
    total_plans = len(plans)
    planned = len([p for p in plans if p.status == PostStatus.PLANNED])
    generated = len([p for p in plans if p.status == PostStatus.GENERATED])
    
    # Success rate
    success_rate = (posted / total_posts * 100) if total_posts > 0 else 0
    
    return {
        "period_days": days,
        "posts": {
            "total": total_posts,
            "posted": posted,
            "failed": failed,
            "pending": pending,
            "success_rate": round(success_rate, 2)
        },
        "plans": {
            "total": total_plans,
            "planned": planned,
            "generated": generated
        }
    }


@router.get("/upcoming")
async def get_upcoming_posts(
    account_id: Optional[int] = None,
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming scheduled posts."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=hours)
    
    query = select(Post).where(
        and_(
            Post.scheduled_time >= now,
            Post.scheduled_time <= future,
            Post.status.in_([PostStatus.GENERATED, PostStatus.SCHEDULED])
        )
    ).order_by(Post.scheduled_time)
    
    if account_id:
        query = query.where(Post.account_id == account_id)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return {
        "count": len(posts),
        "posts": [
            {
                "id": p.id,
                "account_id": p.account_id,
                "text": p.text[:100] + "..." if len(p.text) > 100 else p.text,
                "scheduled_time": p.scheduled_time,
                "status": p.status
            }
            for p in posts
        ]
    }


@router.get("/recent")
async def get_recent_activity(
    account_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get recent activity logs."""
    query = select(ActivityLog)
    
    if account_id:
        query = query.where(ActivityLog.account_id == account_id)
    
    query = query.order_by(ActivityLog.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "message": log.message,
                "created_at": log.created_at,
                "error_details": log.error_details
            }
            for log in logs
        ]
    }


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    from app.llm import get_llm_client
    from app.publishers import get_publisher
    
    # Check database
    try:
        await db.execute(select(Account).limit(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check LLM
    try:
        llm_client = get_llm_client()
        llm_healthy = await llm_client.health_check()
        llm_status = "healthy" if llm_healthy else "unreachable"
    except Exception as e:
        llm_status = f"error: {str(e)}"
    
    # Check publisher
    try:
        publisher = get_publisher()
        publisher_healthy = await publisher.health_check()
        publisher_status = "healthy" if publisher_healthy else "unreachable"
    except Exception as e:
        publisher_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "components": {
            "database": db_status,
            "llm": llm_status,
            "publisher": publisher_status
        }
    }
