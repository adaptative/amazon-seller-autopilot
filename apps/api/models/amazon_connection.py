"""Amazon connection model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AmazonConnection(Base):
    __tablename__ = "amazon_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    marketplace_id: Mapped[str] = mapped_column(String(50), nullable=False)
    seller_id: Mapped[str] = mapped_column(String(50), nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ads_refresh_token_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    connection_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "connection_status IN ('pending', 'active', 'disconnected', 'error')",
            name="ck_amazon_connections_status",
        ),
    )
