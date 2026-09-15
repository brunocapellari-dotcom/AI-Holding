from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel

from second_brain.schemas.contracts import (
    Claim,
    Decision,
    Document,
    Entity,
    Evaluation,
    Event,
    Evidence,
    Fact,
    Learning,
    Method,
    Model,
    Observation,
    Relation,
    Skill,
    Source,
)

SchemaModel: TypeAlias = type[BaseModel]
SCHEMA_MODELS: tuple[SchemaModel, ...] = (
    Source, Document, Observation, Evidence, Claim, Fact, Entity, Relation,
    Event, Method, Model, Skill, Decision, Evaluation, Learning,
)


def export_json_schemas(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in SCHEMA_MODELS:
        path = destination / f"{model.__name__.lower()}.schema.json"
        path.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written
