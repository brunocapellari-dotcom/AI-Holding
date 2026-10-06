from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from second_brain.graph.projection import GraphEpisode

_GROUP_RE = re.compile(r"^[a-zA-Z0-9_-]{2,120}$")


@dataclass(frozen=True)
class GraphitiConfig:
    enabled: bool = False
    telemetry_enabled: bool = False


class GraphitiAdapter:
    """One-way adapter for the derived temporal graph.

    It has no vault-writing API and no method to promote a Claim.
    """

    def __init__(self, client: Any, *, config: GraphitiConfig | None = None) -> None:
        self.client = client
        self.config = config or GraphitiConfig()
        os.environ.setdefault(
            "GRAPHITI_TELEMETRY_ENABLED",
            "true" if self.config.telemetry_enabled else "false",
        )

    async def upsert(self, episode: GraphEpisode) -> None:
        if not self.config.enabled:
            raise RuntimeError("Graphiti projection is disabled")
        if not _GROUP_RE.fullmatch(episode.group_id):
            raise ValueError("invalid Graphiti group_id")
        await self.client.add_episode(
            name=episode.episode_id,
            episode_body=episode.payload,
            group_id=episode.group_id,
        )
