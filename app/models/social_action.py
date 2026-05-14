"""Social action tracking model."""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class SocialAction(Base):
    """Records every social interaction performed by the bot."""

    __tablename__ = "social_actions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # "like" | "reply" | "follow" | "unfollow"
    action_type = Column(String(20), nullable=False, index=True)

    # Threads-side identifiers (may be None for browser-only actions)
    target_post_id = Column(String(200))
    target_user_id = Column(String(200))

    # For replies: the text that was posted
    content = Column(Text)

    success = Column(Boolean, default=True, nullable=False)
    error = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    account = relationship("Account", back_populates="social_actions")
