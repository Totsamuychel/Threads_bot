"""Activity logging model."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ActivityLog(Base):
    """Log of all system activities."""
    
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    
    # Event Details
    event_type = Column(String(50), nullable=False, index=True)
    event_category = Column(String(50), index=True)
    message = Column(Text, nullable=False)
    
    # Context
    post_id = Column(Integer, nullable=True)
    content_plan_id = Column(Integer, nullable=True)
    
    # Additional Data
    event_metadata = Column(JSON)
    error_details = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, default=_utcnow, index=True)
    
    # Relationships
    account = relationship("Account", back_populates="logs")
    
    def __repr__(self):
        return f"<ActivityLog {self.event_type}: {self.message[:50]}>"
