"""Main API router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.trades import router as trades_router
from app.api.portfolio import router as portfolio_router
from app.api.signals import router as signals_router
from app.api.audit import router as audit_router
from app.api.settings import router as settings_router

api_router = APIRouter()

api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(trades_router, prefix="/trades", tags=["trades"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(signals_router, prefix="/signals", tags=["signals"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
