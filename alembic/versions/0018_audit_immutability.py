"""make audit events append-only in PostgreSQL

Revision ID: 0018_audit_immutability
Revises: 0017_human_rbac
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0018_audit_immutability"
down_revision: str | None = "0017_human_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCTION_NAME = "holding_reject_audit_event_mutation"
TRIGGER_NAME = "trg_audit_events_append_only"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {TRIGGER_NAME}
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW
        EXECUTE FUNCTION {FUNCTION_NAME}();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON audit_events")
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()")
