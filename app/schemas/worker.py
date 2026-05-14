"""Worker schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkerCreate(BaseModel):
    """Schema for registering a worker."""
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1)
    port: int = 11434
    api_type: str = "ollama"


class WorkerUpdate(BaseModel):
    """Schema for updating a worker."""
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    api_type: Optional[str] = None


class WorkerHeartbeat(BaseModel):
    """Schema for worker heartbeat with resource metrics."""
    gpu_name: Optional[str] = None
    vram_total_mb: Optional[int] = None
    vram_used_mb: Optional[int] = None
    vram_free_mb: Optional[int] = None
    ram_total_mb: Optional[int] = None
    ram_used_mb: Optional[int] = None
    ram_free_mb: Optional[int] = None
    cpu_percent: Optional[float] = None
    models_available: List[str] = Field(default_factory=list)


class WorkerHeartbeatResponse(BaseModel):
    """Response sent back to worker after heartbeat — includes pull instructions."""
    status: str = "ok"
    required_models: List[str] = Field(default_factory=list)


class WorkerResponse(BaseModel):
    """Schema for worker response."""
    id: int
    name: str
    host: str
    port: int
    api_type: str
    gpu_name: Optional[str] = None
    vram_total_mb: Optional[int] = None
    vram_used_mb: Optional[int] = None
    vram_free_mb: Optional[int] = None
    ram_total_mb: Optional[int] = None
    ram_used_mb: Optional[int] = None
    ram_free_mb: Optional[int] = None
    cpu_percent: Optional[float] = None
    is_online: bool = False
    last_heartbeat: Optional[datetime] = None
    models_available: Optional[List[str]] = None
    required_models: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
