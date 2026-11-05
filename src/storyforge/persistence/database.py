"""Explicit engine/session lifecycle. Never echo SQL containing child data."""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_database(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url, echo=False, hide_parameters=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)
