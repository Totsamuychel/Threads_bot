"""Main FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
from app.api import api_router
from app.api.pages import router as pages_router
from app.scheduler import init_scheduler, start_scheduler, shutdown_scheduler

# Ensure logs directory exists before configuring file handler
os.makedirs(os.path.dirname(settings.log_file) or "logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Threads Automation application")
    await init_db()
    logger.info("Database initialized")
    init_scheduler()
    start_scheduler()
    logger.info("Scheduler started")
    
    yield
    
    logger.info("Shutting down application")
    shutdown_scheduler()
    logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automated Threads content generation and posting system",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routes
app.include_router(api_router)

# Include page routes (must be after API routes so /api/* takes priority)
app.include_router(pages_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
