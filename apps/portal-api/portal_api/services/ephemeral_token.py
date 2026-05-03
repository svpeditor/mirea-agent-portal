"""Генерация и резолв ephemeral OpenRouter-совместимых ключей на job."""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import AgentVersion, EphemeralToken


@dataclass(frozen=True)
class EphemeralTokenContext:
    """Resolved context из ephemeral-токена."""

    user_id: uuid.UUID
    agent_id: uuid.UUID
    agent_version_id: uuid.UUID
    job_id: uuid.UUID


def generate() -> tuple[str, str]:
    """Возвращает (plaintext, sha256_hex). Plaintext: 'por-job-<uuid4_hex>'."""
    plain = "por-job-" + uuid.uuid4().hex
    return plain, hash_token(plain)


def hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


async def insert(
    db: AsyncSession,
    *,
    plaintext: str,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    ttl: timedelta,
) -> None:
    """Сохраняет sha256(plaintext) с TTL. Plaintext НЕ хранится."""
    token = EphemeralToken(
        token_hash=hash_token(plaintext),
        job_id=job_id,
        user_id=user_id,
        agent_version_id=agent_version_id,
        expires_at=datetime.now(timezone.utc) + ttl,
    )
    db.add(token)


async def resolve(
    db: AsyncSession, plaintext: str,
) -> EphemeralTokenContext | None:
    """Резолвит plaintext в context. None если token не найден / истёк / отозван."""
    h = hash_token(plaintext)
    now = datetime.now(timezone.utc)

    stmt = (
        sa.select(EphemeralToken, AgentVersion.agent_id)
        .join(AgentVersion, AgentVersion.id == EphemeralToken.agent_version_id)
        .where(
            EphemeralToken.token_hash == h,
            EphemeralToken.revoked_at.is_(None),
            EphemeralToken.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None

    token, agent_id = row
    return EphemeralTokenContext(
        user_id=token.user_id,
        agent_id=agent_id,
        agent_version_id=token.agent_version_id,
        job_id=token.job_id,
    )


async def revoke_by_job(db: AsyncSession, job_id: uuid.UUID) -> None:
    """Помечает все ephemeral-токены job'а как отозванные. Идемпотентно."""
    now = datetime.now(timezone.utc)
    await db.execute(
        sa.update(EphemeralToken)
        .where(
            EphemeralToken.job_id == job_id,
            EphemeralToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
