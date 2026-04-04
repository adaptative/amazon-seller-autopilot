"""Tenant model."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="starter",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "subscription_tier IN ('starter', 'growth', 'professional', 'enterprise')",
            name="ck_tenants_subscription_tier",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'trial', 'cancelled')",
            name="ck_tenants_status",
        ),
    )
