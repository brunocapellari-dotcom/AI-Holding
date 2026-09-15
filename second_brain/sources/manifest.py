from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from second_brain.schemas import InformationClass
from second_brain.sources.collector_registry import (
    CollectorMethod,
    CollectorRegistry,
    CollectorSpec,
)


def load_collector_manifest(path: Path) -> CollectorRegistry:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("collector manifest must be a mapping")
    if str(loaded.get("schema_version")) != "1.0":
        raise ValueError("unsupported collector manifest schema_version")
    entries = loaded.get("collectors")
    if not isinstance(entries, list):
        raise ValueError("collector manifest must contain a collectors list")

    registry = CollectorRegistry()
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise ValueError(f"collector entry {index} must be a mapping")
        _reject_secret_keys(raw, f"collectors[{index}]")
        try:
            spec = CollectorSpec(
                collector_id=str(raw["collector_id"]),
                source_id=str(raw["source_id"]),
                namespace=str(raw["namespace"]),
                method=CollectorMethod(str(raw["method"])),
                frequency_seconds=int(raw["frequency_seconds"]),
                freshness_seconds=int(raw["freshness_seconds"]),
                max_retries=int(raw.get("max_retries", 3)),
                enabled=bool(raw.get("enabled", True)),
                managed_execution=bool(raw.get("managed_execution", False)),
                owner_project=_optional_str(raw.get("owner_project")),
                source_uri=_optional_str(raw.get("source_uri")),
                information_class=InformationClass(
                    str(raw.get("information_class", InformationClass.INTERNAL.value))
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid collector entry {index}: {exc}") from exc
        registry.register(spec)
    return registry


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _reject_secret_keys(value: Any, path: str) -> None:
    sensitive = {"password", "secret", "token", "api_key", "apikey", "credential", "credentials"}
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in sensitive:
                raise ValueError(f"secret material is forbidden in collector manifests: {path}.{key}")
            _reject_secret_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_secret_keys(item, f"{path}[{index}]")
