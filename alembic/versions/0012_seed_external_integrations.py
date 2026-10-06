"""seed external integration registry

Revision ID: 0012_seed_external_integrations
Revises: 0011_holding_evidence_security
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_seed_external_integrations"
down_revision: str | None = "0011_holding_evidence_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INTEGRATIONS = (
    {
        "id": uuid.UUID("d83a0a85-9c50-4d0d-a87c-15212173b84b"),
        "service_key": "hermes",
        "kind": "ai-platform",
        "status": "unconfigured",
        "endpoint": None,
        "freshness_sla_seconds": 300,
        "metadata_json": {
            "repository": "brunocapellari-dotcom/Hermes-AI-Platform",
            "runtime_evidence": False,
        },
    },
    {
        "id": uuid.UUID("2a78bc1a-4846-42e6-a818-62a36d6476b5"),
        "service_key": "research-ai",
        "kind": "research-platform",
        "status": "unconfigured",
        "endpoint": None,
        "freshness_sla_seconds": 900,
        "metadata_json": {
            "repository": None,
            "runtime_evidence": False,
        },
    },
    {
        "id": uuid.UUID("a0edc40c-540f-4c93-90fc-c1387cb58572"),
        "service_key": "second-brain",
        "kind": "knowledge-platform",
        "status": "unconfigured",
        "endpoint": None,
        "freshness_sla_seconds": 900,
        "metadata_json": {
            "repository": "brunocapellari-dotcom/Second-Brain",
            "runtime_evidence": False,
        },
    },
)


def upgrade() -> None:
    table = sa.table(
        "integration_states",
        sa.column("id", sa.Uuid()),
        sa.column("service_key", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("status", sa.String()),
        sa.column("endpoint", sa.String()),
        sa.column("freshness_sla_seconds", sa.Integer()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(table, list(INTEGRATIONS))


def downgrade() -> None:
    keys = tuple(item["service_key"] for item in INTEGRATIONS)
    op.execute(
        sa.text("DELETE FROM integration_states WHERE service_key IN :keys").bindparams(
            sa.bindparam("keys", value=keys, expanding=True)
        )
    )
