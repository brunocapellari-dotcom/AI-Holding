from __future__ import annotations

import re

PROJECT_ALIASES: dict[str, str] = {
    "agrolog": "project/agrolog",
    "agrologmt": "project/agrolog",
    "mercado-financeiro": "project/mercado-financeiro",
    "finance": "project/mercado-financeiro",
    "geopolitical-watch": "project/geopolitical-watch",
    "geowatch": "project/geopolitical-watch",
    "esportes": "project/esportes",
    "sports-intelligence": "project/esportes",
    "worldwar": "project/worldwar",
    "culinaria": "project/culinaria",
    "holding": "project/holding",
}
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")


def project_namespace(project: str) -> str:
    key = project.strip().lower().replace("_", "-")
    if key in PROJECT_ALIASES:
        return PROJECT_ALIASES[key]
    if not SLUG.fullmatch(key):
        raise ValueError("invalid project namespace slug")
    return f"project/{key}"


def shared_namespace(domain: str | None = None) -> str:
    if not domain:
        return "shared"
    slug = domain.strip().lower().replace("_", "-")
    if not SLUG.fullmatch(slug):
        raise ValueError("invalid shared namespace slug")
    return f"shared/{slug}"
