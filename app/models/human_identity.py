from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HumanRole(StrEnum):
    owner = "owner"
    operator = "operator"
    auditor = "auditor"
    viewer = "viewer"


class HumanIdentityRole(Base):
    __tablename__ = "human_identity_roles"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_human_identity_principal"),
        CheckConstraint(
            "role IN ('owner','operator','auditor','viewer')",
            name="ck_human_identity_role_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
