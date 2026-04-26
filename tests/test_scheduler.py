"""Tests for scheduler tasks."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from app.models import Account, ContentPlan, Post
from app.models.content import PostStatus
from app.services import ContentPlanner


@pytest.mark.asyncio
async def test_content_planner_select_topic():
    """Test topic selection."""
    mock_db = AsyncMock()
    planner = ContentPlanner(mock_db)
    
    topics = ["AI & coding", "productivity", "tech news"]
    
    selected = planner._select_topic(topics)
    
    assert selected in topics


@pytest.mark.asyncio
async def test_content_planner_parse_schedule():
    """Test schedule parsing."""
    mock_db = AsyncMock()
    planner = ContentPlanner(mock_db)
    
    # Test times schedule
    schedule_config = {"times": ["09:00", "14:00", "18:00"]}
    times = planner._parse_schedule(schedule_config)
    
    assert len(times) == 3
    assert "09:00" in times
    assert "14:00" in times
    assert "18:00" in times


def test_post_status_enum():
    """Test PostStatus enum values."""
    assert PostStatus.PLANNED == "planned"
    assert PostStatus.GENERATED == "generated"
    assert PostStatus.POSTED == "posted"
    assert PostStatus.FAILED == "failed"


@pytest.mark.asyncio
async def test_format_post_text_no_hashtags():
    """Test formatting post without hashtags."""
    from app.publishers import MockPublisher
    
    publisher = MockPublisher()
    text = "Test post"
    
    formatted = publisher._format_post_text(text, None)
    
    assert formatted == "Test post"
