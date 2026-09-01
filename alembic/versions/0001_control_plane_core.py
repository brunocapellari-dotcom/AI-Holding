"""holding control plane core

Revision ID: 0001_control_plane_core
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

from app.db.base import Base
from app.models import entities  # noqa: F401

revision: str = "0001_control_plane_core"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
