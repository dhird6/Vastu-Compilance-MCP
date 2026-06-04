from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings


@lru_cache(maxsize=1)
def is_database_enabled() -> bool:
    return bool(get_settings().database_url.strip())


def get_session_factory():
    if not is_database_enabled():
        return None
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=settings.app_debug)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
