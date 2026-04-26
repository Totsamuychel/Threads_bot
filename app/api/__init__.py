"""API routes."""

from fastapi import APIRouter
from app.api import accounts, content, dashboard, workers

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(accounts.router)
api_router.include_router(content.router)
api_router.include_router(dashboard.router)
api_router.include_router(workers.router)

__all__ = ["api_router"]
