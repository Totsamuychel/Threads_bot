"""Account configuration model."""

from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.crypto import EncryptedString


def _utcnow():
    return datetime.now(timezone.utc)


class Account(Base):
    """Threads account configuration."""
    
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    
    # Credentials (api_token is stored encrypted at rest)
    api_token = Column(EncryptedString(700))
    credentials_env_key = Column(String(100))
    
    # Posting Configuration
    timezone = Column(String(50), default="UTC")
    schedule_type = Column(String(20), default="times")
    schedule_config = Column(JSON)
    max_posts_per_day = Column(Integer, default=5)
    
    # Content Configuration
    topics = Column(JSON)
    tone = Column(Text)
    target_audience = Column(Text)
    language = Column(String(10), default="en")
    
    # Hashtag Rules
    base_hashtags = Column(JSON)
    auto_generate_hashtags = Column(Boolean, default=True)
    max_hashtags = Column(Integer, default=5)
    
    # Content Constraints
    min_length = Column(Integer, default=50)
    max_length = Column(Integer, default=500)
    
    # LLM Routing
    llm_model = Column(String(100))  # Per-account model override
    llm_worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    content_plans = relationship("ContentPlan", back_populates="account", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="account", cascade="all, delete-orphan")
    logs = relationship("ActivityLog", back_populates="account", cascade="all, delete-orphan")
    worker = relationship("Worker", back_populates="accounts")
    
    def __repr__(self):
        return f"<Account {self.username}>"
