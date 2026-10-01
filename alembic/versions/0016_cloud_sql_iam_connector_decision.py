"""register Cloud SQL automatic IAM connector decision

Revision ID: 0016_cloud_sql_iam_connector_decision
Revises: 0015_maintenance_tool_decisions
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_cloud_sql_iam_connector_decision"
down_revision: str | None = "0015_maintenance_tool_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEY = "CLOUD_SQL_PYTHON_CONNECTOR_IAM"


def upgrade() -> None:
    table = sa.table(
        "tool_decisions",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("tool_name", sa.String()),
        sa.column("capability", sa.String()),
        sa.column("classification", sa.String()),
        sa.column("replaces_key", sa.String()),
        sa.column("benefit", sa.Text()),
        sa.column("maintenance_cost", sa.Text()),
        sa.column("license", sa.String()),
        sa.column("risk", sa.Text()),
        sa.column("rationale", sa.Text()),
        sa.column("evidence", sa.JSON()),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": uuid.UUID("a20b74fd-c975-4395-84b7-c74b5364f1ac"),
                "key": KEY,
                "tool_name": "Google Cloud SQL Python Connector",
                "capability": "cloud-sql-automatic-iam-authentication",
                "classification": "adopt",
                "replaces_key": "DATABASE_PASSWORD_RUNTIME_AUTH",
                "benefit": "Uses short-lived IAM database authentication through the existing psycopg driver and SQLAlchemy pool.",
                "maintenance_cost": "One official connector dependency; password path retained only as controlled rollback during migration.",
                "license": "Apache-2.0",
                "risk": "Production cutover must not occur until database privileges and private-network connectivity pass acceptance.",
                "rationale": "Removes long-lived database credentials from the primary runtime path without introducing a second database driver or proxy service.",
                "evidence": [
                    "app/db/engine.py",
                    "infra/terraform/database_iam.tf",
                    "github:GoogleCloudPlatform/cloud-sql-python-connector@v1.22.0",
                ],
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM tool_decisions WHERE key = :key").bindparams(key=KEY))
