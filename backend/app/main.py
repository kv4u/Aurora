"""AURORA — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.aurora_log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aurora")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  AURORA Trading System Starting...")
    logger.info(f"  Mode: {settings.aurora_mode.upper()}")
    logger.info(f"  Watchlist: {len(settings.watchlist_symbols)} symbols")
    logger.info("=" * 60)

    # TODO: Initialize scheduler, connect to Redis, start background workers
    yield

    logger.info("AURORA Trading System shutting down...")
    # TODO: Graceful shutdown of scheduler and workers


app = FastAPI(
    title="AURORA",
    description="Automated Unified Real-time Orchestrated Analytics — Trading System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """System health endpoint."""
    return {
        "status": "online",
        "system": "AURORA",
        "mode": settings.aurora_mode,
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AURORA",
        "tagline": "Automated Unified Real-time Orchestrated Analytics",
        "status": "running",
        "docs": "/docs",
    }


# API routers will be registered here as they're built
# from app.api.router import api_router
# app.include_router(api_router, prefix="/api/v1")
