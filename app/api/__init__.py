"""API routes."""

from fastapi import APIRouter, Depends
from app.api import accounts, content, dashboard, workers
from app.auth import require_auth

# All /api/* endpoints require HTTP Basic Auth
api_router = APIRouter(dependencies=[Depends(require_auth)])
api_router.include_router(accounts.router)
api_router.include_router(content.router)
api_router.include_router(dashboard.router)
api_router.include_router(workers.router)

# OAuth callback is excluded from auth — browser redirect cannot send Basic Auth headers
public_router = APIRouter()
public_router.add_api_route(
    "/api/accounts/oauth/callback",
    accounts.oauth_callback,
    methods=["GET"],
    include_in_schema=False,
)

__all__ = ["api_router", "public_router"]
