"""Account schemas."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class AccountBase(BaseModel):
    """Base account schema."""
    username: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    timezone: str = "UTC"
    schedule_type: str = "times"
    schedule_config: dict = Field(default_factory=dict)
    max_posts_per_day: int = 5
    topics: List[str] = Field(default_factory=list)
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    language: str = "en"
    base_hashtags: List[str] = Field(default_factory=list)
    auto_generate_hashtags: bool = True
    max_hashtags: int = 5
    min_length: int = 50
    max_length: int = 500
    llm_model: Optional[str] = None
    llm_worker_id: Optional[int] = None
    is_active: bool = True


class AccountCreate(AccountBase):
    """Schema for creating an account."""
    api_token: Optional[str] = None
    credentials_env_key: Optional[str] = None


class AccountUpdate(BaseModel):
    """Schema for updating an account."""
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    max_posts_per_day: Optional[int] = None
    topics: Optional[List[str]] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    language: Optional[str] = None
    base_hashtags: Optional[List[str]] = None
    auto_generate_hashtags: Optional[bool] = None
    max_hashtags: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    llm_model: Optional[str] = None
    llm_worker_id: Optional[int] = None
    is_active: Optional[bool] = None
    api_token: Optional[str] = None


class AccountResponse(AccountBase):
    """Schema for account response."""
    id: int
    threads_user_id: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
