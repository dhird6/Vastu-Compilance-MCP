"""PostgreSQL + pgvector persistence (optional when DATABASE_URL is set)."""

from __future__ import annotations

from app.db.session import get_session_factory, is_database_enabled
from app.db.vector_store import VedicVectorStore

__all__ = ["get_session_factory", "is_database_enabled", "VedicVectorStore"]
