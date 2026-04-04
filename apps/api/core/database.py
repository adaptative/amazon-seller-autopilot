"""Database engine and session management."""

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that provides a database session."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session


def reset_engine():
    """Reset engine — useful for tests."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
