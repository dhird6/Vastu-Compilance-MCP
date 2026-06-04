from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.models.schemas import RoomOrientation, VedicKnowledgeEntry


class VedicKnowledgeService:
    def __init__(self, knowledge_path: Path) -> None:
        self.knowledge_path = knowledge_path
        self.entries: list[VedicKnowledgeEntry] = self._load_entries(knowledge_path)

    def _load_entries(self, knowledge_path: Path) -> list[VedicKnowledgeEntry]:
        if not knowledge_path.exists():
            return []
        suffix = knowledge_path.suffix.lower()
        with knowledge_path.open("r", encoding="utf-8") as file:
            if suffix in {".yaml", ".yml"}:
                raw = yaml.safe_load(file) or {}
            elif suffix == ".json":
                raw = json.load(file) or {}
            else:
                raise ValueError(f"Unsupported knowledge format: {knowledge_path.suffix}")
        return [VedicKnowledgeEntry.model_validate(entry) for entry in raw.get("entries", [])]

    def ingest_entries(self, entries: list[VedicKnowledgeEntry]) -> dict[str, int]:
        self.entries.extend(entries)
        return {"loaded_entries": len(entries), "total_entries": len(self.entries)}

    def get_references_for(self, room: RoomOrientation, is_failure: bool) -> list[str]:
        references: list[str] = []
        room_type = room.room_type.strip().lower()
        zone = room.zone.strip().lower()
        for entry in self.entries:
            room_match = not entry.room_types or room_type in [item.strip().lower() for item in entry.room_types]
            if not room_match:
                continue
            preferred = [item.strip().lower() for item in entry.preferred_zones]
            avoided = [item.strip().lower() for item in entry.avoid_zones]
            zone_relevant = (zone in preferred) or (zone in avoided) or (not preferred and not avoided)
            if not zone_relevant:
                continue
            polarity_match = (is_failure and zone in avoided) or ((not is_failure) and zone in preferred) or (not preferred and not avoided)
            if polarity_match:
                references.append(f"{entry.source}: {entry.guidance}")
        return references[:3]
