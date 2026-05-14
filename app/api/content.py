"""Content and post management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from app.database import get_db
from app.models import ContentPlan, Post
from app.models.content import PostStatus
from app.schemas import ContentPlanResponse, PostResponse, PostCreate, SuccessResponse
from app.services import ContentPlanner, PostGenerator, PostPublisher

router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/plan/{account_id}", response_model=SuccessResponse)
async def generate_content_plan(
    account_id: int,
    days_ahead: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Generate content plan for an account."""
    planner = ContentPlanner(db)
    plans = await planner.generate_plan_for_account(account_id, days_ahead)
    
    return SuccessResponse(
        message=f"Generated {len(plans)} content plans",
        data={"plans_created": len(plans)}
    )


@router.get("/plans", response_model=List[ContentPlanResponse])
async def list_content_plans(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List content plans with optional filters."""
    query = select(ContentPlan)
    
    if account_id:
        query = query.where(ContentPlan.account_id == account_id)
    
    if status:
        query = query.where(ContentPlan.status == status)
    
    query = query.order_by(ContentPlan.scheduled_time).offset(skip).limit(limit)
    
    result = await db.execute(query)
    plans = result.scalars().all()
    
    return plans


@router.post("/generate/{plan_id}", response_model=PostResponse)
async def generate_post(plan_id: int, db: AsyncSession = Depends(get_db)):
    """Generate a post for a content plan."""
    generator = PostGenerator(db)
    post = await generator.generate_post_for_plan(plan_id)
    
    if not post:
        raise HTTPException(status_code=500, detail="Failed to generate post")
    
    return post


@router.post("/publish/{post_id}", response_model=SuccessResponse)
async def publish_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Publish a post immediately."""
    publisher = PostPublisher(db)
    success = await publisher.publish_post(post_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to publish post")
    
    return SuccessResponse(message=f"Post {post_id} published successfully")


@router.post("/retry/{post_id}", response_model=SuccessResponse)
async def retry_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Retry publishing a failed post."""
    publisher = PostPublisher(db)
    success = await publisher.retry_failed_post(post_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to retry post")
    
    return SuccessResponse(message=f"Post {post_id} retried successfully")


@router.get("/posts", response_model=List[PostResponse])
async def list_posts(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List posts with optional filters."""
    query = select(Post)
    
    if account_id:
        query = query.where(Post.account_id == account_id)
    
    if status:
        query = query.where(Post.status == status)
    
    query = query.order_by(desc(Post.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return posts


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get post by ID."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_manual_post(post: PostCreate, db: AsyncSession = Depends(get_db)):
    """Create a manual post (without LLM generation)."""
    db_post = Post(**post.model_dump())
    db_post.status = PostStatus.GENERATED
    
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    
    return db_post


@router.delete("/posts/{post_id}", response_model=SuccessResponse)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()

    return SuccessResponse(message=f"Post {post_id} deleted successfully")


# ------------------------------------------------------------------
# Social activity endpoints
# ------------------------------------------------------------------

@router.post("/activity/{account_id}/run", response_model=SuccessResponse)
async def run_social_activity(account_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger a social activity session (likes, replies, follows) for an account."""
    from app.services.social_actions import SocialActionsService
    service = SocialActionsService(db, account_id)
    result = await service.run()
    return SuccessResponse(
        message="Social activity session completed",
        data=result,
    )


@router.post("/activity/{account_id}/reply", response_model=SuccessResponse)
async def post_api_reply(
    account_id: int,
    thread_id: str = Query(..., description="Threads post ID to reply to"),
    text: str = Query(..., description="Reply text (max 500 chars)"),
    db: AsyncSession = Depends(get_db),
):
    """Post a reply to a Threads post via the official API."""
    from app.publishers.threads_api import ThreadsAPIPublisher
    publisher = ThreadsAPIPublisher(db=db)
    result = await publisher.reply_to_thread(account_id, thread_id, text)
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error)
    return SuccessResponse(
        message="Reply posted successfully",
        data={"post_id": result.post_id, "post_url": result.post_url},
    )


@router.get("/activity/{account_id}/stats", response_model=SuccessResponse)
async def get_activity_stats(
    account_id: int,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Return social action counts for the past N days."""
    from app.models.social_action import SocialAction
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(SocialAction.action_type, func.count(SocialAction.id))
        .where(
            and_(
                SocialAction.account_id == account_id,
                SocialAction.success == True,
                SocialAction.created_at >= since,
            )
        )
        .group_by(SocialAction.action_type)
    )
    stats = {row[0]: row[1] for row in result.all()}
    return SuccessResponse(message="Activity stats", data=stats)
