"""Content planning service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Account, ContentPlan
from app.models.content import PostStatus
from app.config import settings
import random
import pytz

logger = logging.getLogger(__name__)


class ContentPlanner:
    """Service for generating and managing content plans."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_plan_for_account(self, account_id: int, days_ahead: Optional[int] = None) -> List[ContentPlan]:
        """
        Generate content plan for an account for the next N days.
        
        Args:
            account_id: Account to plan for
            days_ahead: Number of days to plan ahead (defaults to settings)
            
        Returns:
            List of created ContentPlan objects
        """
        days_ahead = days_ahead or settings.content_plan_days_ahead
        
        # Get account
        result = await self.db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        
        if not account or not account.is_active:
            logger.warning(f"Account {account_id} not found or inactive")
            return []
        
        # Parse timezone
        tz = pytz.timezone(account.timezone)
        now = datetime.now(tz)
        
        # Get posting times from schedule config
        posting_times = self._parse_schedule(account.schedule_config)
        
        if not posting_times:
            logger.warning(f"No posting times configured for account {account_id}")
            return []
        
        # Generate plans for each day
        created_plans = []
        
        for day_offset in range(days_ahead):
            target_date = now + timedelta(days=day_offset)
            
            # Skip if we already have plans for this day
            existing_count = await self._count_plans_for_day(account_id, target_date)
            
            if existing_count >= len(posting_times):
                logger.debug(f"Plans already exist for {target_date.date()}")
                continue
            
            # Create plans for each posting time
            for time_str in posting_times:
                # Parse time
                hour, minute = map(int, time_str.split(":"))
                scheduled_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Skip if in the past
                if scheduled_time < now:
                    continue
                
                # Check if plan already exists for this time
                existing = await self._get_plan_for_time(account_id, scheduled_time)
                if existing:
                    continue
                
                # Select a topic
                topic = self._select_topic(account.topics)
                
                # Create content plan
                plan = ContentPlan(
                    account_id=account_id,
                    topic=topic,
                    scheduled_time=scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None),
                    status=PostStatus.PLANNED,
                    llm_model=settings.llm_model,
                    llm_temperature=settings.llm_temperature,
                    llm_max_tokens=settings.llm_max_tokens
                )
                
                self.db.add(plan)
                created_plans.append(plan)
                
                logger.info(f"Created plan: {topic} @ {scheduled_time}")
        
        await self.db.commit()
        
        logger.info(f"Generated {len(created_plans)} content plans for account {account_id}")
        return created_plans
    
    async def get_upcoming_plans(self, account_id: Optional[int] = None, 
                                hours_ahead: int = 24) -> List[ContentPlan]:
        """
        Get upcoming content plans.
        
        Args:
            account_id: Optional account filter
            hours_ahead: Look ahead this many hours
            
        Returns:
            List of upcoming ContentPlan objects
        """
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=hours_ahead)
        
        query = select(ContentPlan).where(
            and_(
                ContentPlan.scheduled_time >= now,
                ContentPlan.scheduled_time <= future,
                ContentPlan.status == PostStatus.PLANNED
            )
        )
        
        if account_id:
            query = query.where(ContentPlan.account_id == account_id)
        
        query = query.order_by(ContentPlan.scheduled_time)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    def _parse_schedule(self, schedule_config: dict) -> List[str]:
        """Parse schedule configuration to get posting times."""
        if not schedule_config:
            return []
        
        if "times" in schedule_config:
            return schedule_config["times"]
        
        # TODO: Add CRON parsing if needed
        return []
    
    async def _count_plans_for_day(self, account_id: int, target_date: datetime) -> int:
        """Count existing plans for a specific day."""
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Convert to UTC
        start_utc = start_of_day.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_of_day.astimezone(pytz.UTC).replace(tzinfo=None)
        
        result = await self.db.execute(
            select(ContentPlan).where(
                and_(
                    ContentPlan.account_id == account_id,
                    ContentPlan.scheduled_time >= start_utc,
                    ContentPlan.scheduled_time < end_utc
                )
            )
        )
        
        return len(list(result.scalars().all()))
    
    async def _get_plan_for_time(self, account_id: int, scheduled_time: datetime) -> Optional[ContentPlan]:
        """Check if a plan exists for a specific time."""
        scheduled_utc = scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)
        
        result = await self.db.execute(
            select(ContentPlan).where(
                and_(
                    ContentPlan.account_id == account_id,
                    ContentPlan.scheduled_time == scheduled_utc
                )
            )
        )
        
        return result.scalar_one_or_none()
    
    def _select_topic(self, topics: List[str]) -> str:
        """Select a topic from the list."""
        if not topics:
            return "General content"
        
        return random.choice(topics)
