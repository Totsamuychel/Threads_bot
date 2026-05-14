"""Worker management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from fastapi import Body
from datetime import datetime, timezone
from app.database import get_db
from app.models import Worker
from app.schemas import WorkerCreate, WorkerUpdate, WorkerResponse, WorkerHeartbeat, WorkerHeartbeatResponse, SuccessResponse

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.post("", response_model=WorkerResponse, status_code=201)
async def create_worker(worker: WorkerCreate, db: AsyncSession = Depends(get_db)):
    """Register a new worker node."""
    result = await db.execute(select(Worker).where(Worker.name == worker.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Worker name already exists")
    
    db_worker = Worker(**worker.model_dump())
    db.add(db_worker)
    await db.commit()
    await db.refresh(db_worker)
    return db_worker


@router.get("", response_model=List[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    """List all worker nodes."""
    result = await db.execute(select(Worker).order_by(Worker.name))
    return result.scalars().all()


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(worker_id: int, db: AsyncSession = Depends(get_db)):
    """Get worker by ID."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(worker_id: int, update: WorkerUpdate, db: AsyncSession = Depends(get_db)):
    """Update worker configuration."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(worker, field, value)
    
    await db.commit()
    await db.refresh(worker)
    return worker


@router.delete("/{worker_id}", response_model=SuccessResponse)
async def delete_worker(worker_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a worker node."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    await db.delete(worker)
    await db.commit()
    return SuccessResponse(message=f"Worker '{worker.name}' deleted")


@router.post("/{worker_id}/heartbeat", response_model=WorkerHeartbeatResponse)
async def worker_heartbeat(worker_id: int, heartbeat: WorkerHeartbeat, db: AsyncSession = Depends(get_db)):
    """Receive heartbeat; respond with list of models the worker should pull."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.gpu_name = heartbeat.gpu_name
    worker.vram_total_mb = heartbeat.vram_total_mb
    worker.vram_used_mb = heartbeat.vram_used_mb
    worker.vram_free_mb = heartbeat.vram_free_mb
    worker.ram_total_mb = heartbeat.ram_total_mb
    worker.ram_used_mb = heartbeat.ram_used_mb
    worker.ram_free_mb = heartbeat.ram_free_mb
    worker.cpu_percent = heartbeat.cpu_percent
    worker.models_available = heartbeat.models_available
    worker.is_online = True
    worker.last_heartbeat = datetime.now(timezone.utc)

    await db.commit()

    # Tell worker which models to pull (ones not yet available)
    required = worker.required_models or []
    available = set(heartbeat.models_available)
    to_pull = [m for m in required if m not in available]
    return WorkerHeartbeatResponse(required_models=to_pull)


@router.put("/{worker_id}/required-models", response_model=WorkerResponse)
async def set_required_models(worker_id: int, models: List[str] = Body(...), db: AsyncSession = Depends(get_db)):
    """Set the list of models that must be available on this worker."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.required_models = models
    await db.commit()
    await db.refresh(worker)
    return worker


@router.post("/register", response_model=WorkerResponse, status_code=201)
async def auto_register_worker(worker: WorkerCreate, db: AsyncSession = Depends(get_db)):
    """Auto-register: create if not exists, return existing if found."""
    result = await db.execute(select(Worker).where(Worker.name == worker.name))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.host = worker.host
        existing.port = worker.port
        existing.api_type = worker.api_type
        existing.is_online = True
        existing.last_heartbeat = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return existing
    
    db_worker = Worker(**worker.model_dump(), is_online=True, last_heartbeat=datetime.now(timezone.utc))
    db.add(db_worker)
    await db.commit()
    await db.refresh(db_worker)
    return db_worker
