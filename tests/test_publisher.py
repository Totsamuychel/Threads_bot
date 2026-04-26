"""Tests for publishers."""

import pytest
from app.publishers import get_publisher, MockPublisher
from app.publishers.base import PublishResult


@pytest.mark.asyncio
async def test_mock_publisher_success():
    """Test mock publisher successful publishing."""
    publisher = MockPublisher()
    
    result = await publisher.publish(
        account_id=1,
        text="Test post content",
        hashtags=["test", "automation"]
    )
    
    assert result.success
    assert result.post_id is not None
    assert result.post_url is not None
    assert result.published_at is not None
    assert len(publisher.published_posts) == 1


@pytest.mark.asyncio
async def test_mock_publisher_health_check():
    """Test mock publisher health check."""
    publisher = MockPublisher()
    
    is_healthy = await publisher.health_check()
    
    assert is_healthy is True


@pytest.mark.asyncio
async def test_mock_publisher_account_info():
    """Test mock publisher account info."""
    publisher = MockPublisher()
    
    # Publish a post first
    await publisher.publish(account_id=1, text="Test")
    
    info = await publisher.get_account_info(account_id=1)
    
    assert info is not None
    assert info["id"] == 1
    assert info["posts_count"] == 1


def test_get_publisher_mock():
    """Test publisher factory for mock."""
    publisher = get_publisher(publisher_type="mock")
    assert isinstance(publisher, MockPublisher)


def test_get_publisher_invalid():
    """Test publisher factory with invalid type."""
    with pytest.raises(ValueError):
        get_publisher(publisher_type="invalid")


@pytest.mark.asyncio
async def test_format_post_text():
    """Test post text formatting with hashtags."""
    publisher = MockPublisher()
    
    text = "This is a test post"
    hashtags = ["test", "#automation", "threads"]
    
    formatted = publisher._format_post_text(text, hashtags)
    
    assert "This is a test post" in formatted
    assert "#test" in formatted
    assert "#automation" in formatted
    assert "#threads" in formatted
