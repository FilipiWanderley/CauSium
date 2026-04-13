from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    revoked_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column()

async def revoke_all_tokens_for_user(db: AsyncSession, user_id: UUID):
    # Marca todos os tokens do usuário como revogados (por JTI, se disponível)
    # Para tokens JWT sem JTI, pode-se usar um timestamp de "revogado após"
    # Aqui, para simplicidade, vamos usar um registro de "revogado após" por user_id
    await db.execute(delete(RevokedToken).where(RevokedToken.user_id == user_id))
    revoked = RevokedToken(
        jti="*", user_id=user_id, revoked_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(revoked)
    await db.flush()

async def is_token_revoked(db: AsyncSession, user_id: UUID, issued_at: datetime) -> bool:
    # Verifica se existe um registro de revogação posterior ao issued_at
    result = await db.execute(
        select(RevokedToken).where(
            RevokedToken.user_id == user_id,
            RevokedToken.revoked_at > issued_at,
        )
    )
    return result.scalar_one_or_none() is not None
