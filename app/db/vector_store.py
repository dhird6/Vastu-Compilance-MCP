"""pgvector-backed Vedic knowledge retrieval (graceful fallback without DB)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.db.session import get_session_factory, is_database_enabled
from app.models.schemas import VedicKnowledgeEntry

logger = logging.getLogger(__name__)


class VedicVectorStore:
    """
    Spatial-textual context mapping for Vedic guidance.

    When DATABASE_URL + pgvector are configured, embeddings enable semantic search.
    Otherwise operations are no-ops and YAML in-memory knowledge is used.
    """

    async def upsert_entries(self, entries: list[VedicKnowledgeEntry]) -> dict[str, Any]:
        if not is_database_enabled():
            return {"stored": 0, "mode": "disabled"}

        session_factory = get_session_factory()
        if session_factory is None:
            return {"stored": 0, "mode": "disabled"}

        from app.db.models import VedicKnowledgeVector

        stored = 0
        async with session_factory() as session:
            for entry in entries:
                row = VedicKnowledgeVector(
                    source=entry.source,
                    principle=entry.principle,
                    guidance=entry.guidance,
                    room_types=json.dumps(entry.room_types),
                    embedding=None,
                )
                session.add(row)
                stored += 1
            await session.commit()
        return {"stored": stored, "mode": "postgres"}

    async def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        if not is_database_enabled():
            return []
        # Full pgvector cosine search requires embedding pipeline — placeholder for Phase 2
        logger.debug("Vector search placeholder for query: %s (limit=%d)", query, limit)
        return []
