#!/usr/bin/env python
"""Script to create an example account configuration."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import AsyncSessionLocal
from app.models import Account


async def create_example_account():
    """Create an example account with sensible defaults."""
    
    async with AsyncSessionLocal() as db:
        # Check if account already exists
        from sqlalchemy import select
        result = await db.execute(select(Account).where(Account.username == "example_account"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Account 'example_account' already exists (ID: {existing.id})")
            return existing.id
        
        # Create new account
        account = Account(
            username="example_account",
            display_name="Example Tech Content Creator",
            timezone="America/New_York",
            schedule_type="times",
            schedule_config={
                "times": ["09:00", "14:00", "18:00"]
            },
            max_posts_per_day=3,
            topics=[
                "AI and machine learning",
                "coding tips and tricks",
                "developer productivity",
                "tech industry insights",
                "software engineering best practices"
            ],
            tone="casual, witty, educational",
            target_audience="developers and tech enthusiasts aged 25-40",
            language="en",
            base_hashtags=["#coding", "#tech", "#AI"],
            auto_generate_hashtags=True,
            max_hashtags=5,
            min_length=150,
            max_length=400,
            is_active=True
        )
        
        db.add(account)
        await db.commit()
        await db.refresh(account)
        
        print(f"✅ Created example account (ID: {account.id})")
        print(f"   Username: {account.username}")
        print(f"   Topics: {', '.join(account.topics)}")
        print(f"   Schedule: {', '.join(account.schedule_config['times'])}")
        print(f"\nNext steps:")
        print(f"1. Generate content plan: curl -X POST http://localhost:8000/api/content/plan/{account.id}")
        print(f"2. View plans: curl http://localhost:8000/api/content/plans?account_id={account.id}")
        print(f"3. Check dashboard: curl http://localhost:8000/api/dashboard/upcoming")
        
        return account.id


if __name__ == "__main__":
    asyncio.run(create_example_account())
