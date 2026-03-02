"""AURORA — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.security.rate_limiter import RateLimiter

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.aurora_log_level),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aurora")

# Scheduler instance (created during lifespan)
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    global _scheduler

    logger.info("=" * 60)
    logger.info("  AURORA Trading System Starting...")
    logger.info(f"  Mode: {settings.aurora_mode.upper()}")
    logger.info(f"  Watchlist: {len(settings.watchlist_symbols)} symbols")
    logger.info("=" * 60)

    # Initialize APScheduler for trading loop
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        from app.api.emergency import is_halted
        from app.core.scheduler import TradingLoop
        from app.database import get_db

        _scheduler = AsyncIOScheduler(timezone="US/Eastern")

        async def run_trading_cycle():
            """Wrapper that creates a fresh DB session per cycle."""
            if is_halted():
                logger.warning("Trading cycle skipped — emergency halt active")
                return

            async for db in get_db():
                loop = TradingLoop(settings, db)
                try:
                    results = await loop.run_cycle()
                    logger.info("Cycle results: %s", results)
                finally:
                    await loop.cleanup()

        # Run during market hours: Mon-Fri, 9:35am - 3:55pm ET
        _scheduler.add_job(
            run_trading_cycle,
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{settings.trading_start_hour}-{settings.trading_end_hour}",
                minute=f"*/{settings.signal_interval_minutes}",
                timezone="US/Eastern",
            ),
            id="trading_loop",
            name="AURORA Trading Loop",
            max_instances=1,
        )

        _scheduler.start()
        logger.info(
            "Scheduler started: every %d min, %d:00-%d:00 ET, Mon-Fri",
            settings.signal_interval_minutes,
            settings.trading_start_hour,
            settings.trading_end_hour,
        )
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)
        logger.info("System running in API-only mode (no auto-trading)")

    yield

    # Graceful shutdown
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    logger.info("AURORA Trading System shutting down...")


app = FastAPI(
    title="AURORA",
    description="Automated Unified Real-time Orchestrated Analytics — Trading System",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate Limiter Middleware (must be added before CORS)
app.add_middleware(RateLimiter, max_requests=100, window_seconds=60)

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


# API routers
from app.api.router import api_router  # noqa: E402
from app.api.ws import router as ws_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
