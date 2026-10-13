"""merge Control Plane and Hermes migration heads

Revision ID: 0024_merge_control_plane_hermes
Revises: 0023_control_plane_registry, 0009_hermes_event_receipts
Create Date: 2026-10-13
"""

from collections.abc import Sequence

revision: str = "0024_merge_control_plane_hermes"
down_revision: tuple[str, str] = (
    "0023_control_plane_registry",
    "0009_hermes_event_receipts",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
