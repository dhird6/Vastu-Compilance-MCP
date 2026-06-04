from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ComplianceReportRecord(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    score: Mapped[float] = mapped_column()
    grade: Mapped[str] = mapped_column(String(8))
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class VedicKnowledgeVector(Base):
    __tablename__ = "vedic_knowledge_vectors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(256))
    principle: Mapped[str] = mapped_column(String(512))
    guidance: Mapped[str] = mapped_column(Text)
    room_types: Mapped[str] = mapped_column(Text)
    # embedding stored as pgvector when extension enabled; fallback text for dev
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
