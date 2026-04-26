"""Content and post schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ContentPlanResponse(BaseModel):
    """Schema for content plan response."""
    id: int
    account_id: int
    topic: str
    specific_idea: Optional[str] = None
    scheduled_time: datetime
    status: str
    llm_model: Optional[str] = None
    llm_temperature: Optional[str] = None
    llm_max_tokens: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    """Schema for manually creating a post."""
    account_id: int
    text: str = Field(..., min_length=1)
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    scheduled_time: Optional[datetime] = None


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    account_id: int
    content_plan_id: Optional[int] = None
    text: str
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    scheduled_time: Optional[datetime] = None
    published_at: Optional[datetime] = None
    threads_post_id: Optional[str] = None
    threads_post_url: Optional[str] = None
    status: str
    retry_count: int
    last_error: Optional[str] = None
    llm_model_used: Optional[str] = None
    generation_time_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
