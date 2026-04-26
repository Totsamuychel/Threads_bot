"""Content planning and post models."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PostStatus(str, enum.Enum):
    """Post lifecycle status."""
    PLANNED = "planned"
    GENERATING = "generating"
    GENERATED = "generated"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentPlan(Base):
    """Content plan for a specific post."""
    
    __tablename__ = "content_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Planning
    topic = Column(String(200), nullable=False)
    specific_idea = Column(Text)
    scheduled_time = Column(DateTime, nullable=False, index=True)
    
    # Status
    status = Column(Enum(PostStatus), default=PostStatus.PLANNED, index=True)
    
    # LLM Configuration
    llm_model = Column(String(100))
    llm_temperature = Column(Float)
    llm_max_tokens = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="content_plans")
    post = relationship("Post", back_populates="content_plan", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ContentPlan {self.id}: {self.topic} @ {self.scheduled_time}>"


class Post(Base):
    """Generated and published post."""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    content_plan_id = Column(Integer, ForeignKey("content_plans.id"), nullable=True)
    
    # Content
    text = Column(Text, nullable=False)
    hashtags = Column(JSON)
    media_urls = Column(JSON)
    
    # Generation Metadata
    llm_prompt = Column(Text)
    llm_system_prompt = Column(Text)
    llm_raw_response = Column(Text)
    llm_model_used = Column(String(100))
    generation_time_seconds = Column(Integer)
    
    # Publishing
    scheduled_time = Column(DateTime, index=True)
    published_at = Column(DateTime, index=True)
    threads_post_id = Column(String(200))
    threads_post_url = Column(String(500))
    
    # Status & Retry
    status = Column(Enum(PostStatus), default=PostStatus.GENERATED, index=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="posts")
    content_plan = relationship("ContentPlan", back_populates="post")
    
    def __repr__(self):
        return f"<Post {self.id}: {self.status}>"
