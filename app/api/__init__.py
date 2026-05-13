"""API routes."""

from fastapi import APIRouter, Depends
from app.api import accounts, content, dashboard, workers
from app.auth import require_auth

# Create main API router — all /api/* endpoints require HTTP Basic Auth
api_router = APIRouter(dependencies=[Depends(require_auth)])

# Include sub-routers
api_router.include_router(accounts.router)
api_router.include_router(content.router)
api_router.include_router(dashboard.router)
api_router.include_router(workers.router)

__all__ = ["api_router"]
