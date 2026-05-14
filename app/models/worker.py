"""Worker node model for distributed LLM inference."""

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Worker(Base):
    """Remote worker node running Ollama or compatible LLM server."""
    
    __tablename__ = "workers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=11434)
    api_type = Column(String(20), default="ollama")  # ollama, openai
    
    # Resource Metrics
    gpu_name = Column(String(200))
    vram_total_mb = Column(Integer)
    vram_used_mb = Column(Integer)
    vram_free_mb = Column(Integer)
    ram_total_mb = Column(Integer)
    ram_used_mb = Column(Integer)
    ram_free_mb = Column(Integer)
    cpu_percent = Column(Float)
    
    # Status
    is_online = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime)
    models_available = Column(JSON, default=list)   # reported by worker
    required_models = Column(JSON, default=list)    # set by admin, worker will pull these
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="worker")
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def vram_percent(self) -> float:
        if self.vram_total_mb and self.vram_total_mb > 0:
            return round((self.vram_used_mb or 0) / self.vram_total_mb * 100, 1)
        return 0.0
    
    @property
    def ram_percent(self) -> float:
        if self.ram_total_mb and self.ram_total_mb > 0:
            return round((self.ram_used_mb or 0) / self.ram_total_mb * 100, 1)
        return 0.0
    
    def __repr__(self):
        return f"<Worker {self.name} ({self.host}:{self.port})>"
