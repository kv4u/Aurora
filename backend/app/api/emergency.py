"""Emergency stop endpoint — immediately halts all trading."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.security.auth import require_auth

logger = logging.getLogger("aurora.emergency")

router = APIRouter()

# Module-level flag — checked by the scheduler before each cycle
emergency_halt = False


def is_halted() -> bool:
    """Check if emergency stop is active."""
    return emergency_halt


def clear_halt():
    """Clear emergency halt (called on restart or manual reset)."""
    global emergency_halt
    emergency_halt = False


@router.post("/emergency-stop")
async def emergency_stop(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(require_auth),
):
    """EMERGENCY STOP — immediately halt all trading.

    This will:
    1. Set global halt flag (blocks new trading cycles)
    2. Log the event to audit trail
    3. Attempt to cancel all pending orders via broker

    To resume trading, restart the system.
    """
    global emergency_halt
    emergency_halt = True

    logger.critical("!!! EMERGENCY STOP triggered by user: %s !!!", user)

    # Audit log
    entry = AuditLog(
        event_type="emergency_stop",
        severity="CRITICAL",
        component="emergency",
        details={
            "triggered_by": user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "All trading halted. Pending order cancellation requested.",
        },
    )
    db.add(entry)
    await db.commit()

    # Attempt to cancel orders and close positions via broker
    cancelled_orders = 0
    closed_positions = 0
    try:
        from app.config import get_settings
        from app.core.trade_executor import TradeExecutor

        settings = get_settings()
        executor = TradeExecutor(settings, db, risk_manager=None, audit_logger=None)
        cancelled_orders = await executor.cancel_all_orders()
        closed_positions = await executor.close_all_positions()
        await executor.close()
    except Exception as e:
        logger.error("Error during emergency cleanup: %s", e)

    return {
        "status": "HALTED",
        "message": "Emergency stop activated. All trading halted.",
        "cancelled_orders": cancelled_orders,
        "closed_positions": closed_positions,
        "triggered_by": user,
        "resume": "Restart the system to resume trading.",
    }


@router.post("/resume")
async def resume_trading(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(require_auth),
):
    """Resume trading after emergency stop."""
    global emergency_halt
    was_halted = emergency_halt
    emergency_halt = False

    logger.info("Trading resumed by user: %s (was_halted=%s)", user, was_halted)

    entry = AuditLog(
        event_type="trading_resumed",
        severity="WARNING",
        component="emergency",
        details={
            "triggered_by": user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "was_halted": was_halted,
        },
    )
    db.add(entry)
    await db.commit()

    return {
        "status": "ACTIVE",
        "message": "Trading resumed." if was_halted else "Trading was not halted.",
        "resumed_by": user,
    }
