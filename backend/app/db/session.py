"""
Database Session Management for PM Document Intelligence.

This module handles database connections, session management, and connection pooling
using SQLAlchemy and asyncpg for async PostgreSQL operations.

Features:
- Async database engine with connection pooling
- Session factory for request-scoped sessions
- Health check functionality
- Graceful connection cleanup

Usage:
    from app.db.session import get_db

    async def get_user(user_id: int):
        async with get_db() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.config import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)


# Global engine instance
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """
    Get or create the database engine.

    Returns:
        AsyncEngine instance
    """
    global _engine

    if _engine is None:
        # Get database URL with async driver
        database_url = settings.get_database_url(async_driver=True)

        # Configure pool
        if settings.is_testing:
            # Use NullPool for testing to avoid connection issues
            poolclass = NullPool
            pool_pre_ping = False
        else:
            # Use QueuePool for production/development
            poolclass = QueuePool
            pool_pre_ping = True

        # Create engine
        _engine = create_async_engine(
            database_url,
            poolclass=poolclass,
            pool_size=settings.supabase.database_pool_size if not settings.is_testing else 5,
            max_overflow=settings.supabase.database_max_overflow if not settings.is_testing else 0,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=settings.debug,  # Log SQL queries in debug mode
        )

        logger.info(
            f"Database engine created (pool_size={settings.supabase.database_pool_size})"
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session factory.

    Returns:
        Session factory for creating database sessions
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Database session factory created")

    return _session_factory


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.

    Yields:
        Database session

    Usage:
        async with get_db() as session:
            result = await session.execute(select(User))
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_database_connection() -> bool:
    """
    Test database connectivity.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with get_db() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT 1"))
            result.scalar_one()

        logger.debug("Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}", exc_info=True)
        return False


async def close_database_connections() -> None:
    """
    Close all database connections.

    Called during application shutdown.
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")
        _engine = None

    _session_factory = None
