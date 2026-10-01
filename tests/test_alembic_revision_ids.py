from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_ids_fit_default_version_table() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    oversized = sorted(
        revision.revision
        for revision in script.walk_revisions()
        if len(revision.revision) > 32
    )

    assert oversized == [], (
        "Alembic revision IDs must fit the default alembic_version.version_num "
        f"VARCHAR(32); oversized IDs: {oversized}"
    )
