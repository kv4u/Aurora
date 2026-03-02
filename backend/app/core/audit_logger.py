"""Structured audit logging — records every system decision for full traceability."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("aurora.audit")


class AuditLogger:
    """Every decision, trade, and event is logged with full context."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        event_type: str,
        details: dict,
        *,
        component: str = "system",
        symbol: str | None = None,
        severity: str = "INFO",
        decision_chain_id: uuid.UUID | None = None,
    ) -> AuditLog:
        # Redact any secrets that might accidentally appear
        safe_details = self._redact_secrets(details)

        entry = AuditLog(
            event_type=event_type,
            severity=severity,
            component=component,
            symbol=symbol,
            details=safe_details,
            decision_chain_id=decision_chain_id,
        )
        self.db.add(entry)
        await self.db.flush()

        logger.info(
            "[%s] %s | %s | %s",
            severity,
            component,
            event_type,
            symbol or "—",
        )
        return entry

    async def log_decision_chain(
        self,
        chain_id: uuid.UUID,
        event_type: str,
        details: dict,
        *,
        component: str,
        symbol: str | None = None,
        severity: str = "INFO",
    ) -> AuditLog:
        return await self.log(
            event_type,
            details,
            component=component,
            symbol=symbol,
            severity=severity,
            decision_chain_id=chain_id,
        )

    async def get_decision_chain(self, chain_id: uuid.UUID) -> list[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.decision_chain_id == chain_id)
            .order_by(AuditLog.timestamp)
        )
        return list(result.scalars().all())

    def _redact_secrets(self, data: dict) -> dict:
        """Prevent secrets from leaking into audit logs."""
        sensitive_keys = {
            "api_key", "secret_key", "password", "token", "jwt",
            "anthropic_api_key", "alpaca_api_key", "alpaca_secret_key",
        }
        redacted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                redacted[key] = self._redact_secrets(value)
            elif any(s in key.lower() for s in sensitive_keys):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = value
        return redacted
