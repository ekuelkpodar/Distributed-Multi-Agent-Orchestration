"""
Database connection management for PostgreSQL and Redis.
Provides connection pooling, health checks, and graceful shutdown.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import structlog

logger = structlog.get_logger()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class DatabaseManager:
    """
    Manages PostgreSQL database connections with async support.
    Provides connection pooling and health checks.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://agent_user:agent_pass@localhost:5432/agents_db"
        )
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.echo = echo
        self._engine = None
        self._session_factory = None

    async def initialize(self) -> None:
        """Initialize the database engine and session factory."""
        logger.info("Initializing database connection", url=self._mask_url(self.database_url))

        self._engine = create_async_engine(
            self.database_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            pool_recycle=self.pool_recycle,
            echo=self.echo,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )

        # Test connection
        await self.health_check()
        logger.info("Database connection initialized successfully")

    async def close(self) -> None:
        """Close database connections gracefully."""
        if self._engine:
            logger.info("Closing database connections")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope for database operations.

        Usage:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()

    async def health_check(self) -> dict:
        """Check database health and return status."""
        try:
            async with self.session() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            return {"status": "healthy", "database": "postgresql"}
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {"status": "unhealthy", "database": "postgresql", "error": str(e)}

    def _mask_url(self, url: str) -> str:
        """Mask password in database URL for logging."""
        if "@" in url:
            parts = url.split("@")
            creds = parts[0].split("://")[-1]
            if ":" in creds:
                user = creds.split(":")[0]
                return url.replace(creds, f"{user}:****")
        return url


class RedisManager:
    """
    Manages Redis connections with async support.
    Provides connection pooling and health checks.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 50,
        socket_keepalive: bool = True,
        health_check_interval: int = 30
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_connections = max_connections
        self.socket_keepalive = socket_keepalive
        self.health_check_interval = health_check_interval
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        logger.info("Initializing Redis connection", url=self.redis_url)

        self._pool = redis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            socket_keepalive=self.socket_keepalive,
            health_check_interval=self.health_check_interval,
            decode_responses=True
        )

        self._client = redis.Redis(connection_pool=self._pool)

        # Test connection
        await self.health_check()
        logger.info("Redis connection initialized successfully")

    async def close(self) -> None:
        """Close Redis connections gracefully."""
        if self._client:
            logger.info("Closing Redis connections")
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis connections closed")

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client."""
        if not self._client:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client

    async def health_check(self) -> dict:
        """Check Redis health and return status."""
        try:
            await self.client.ping()
            info = await self.client.info("server")
            return {
                "status": "healthy",
                "database": "redis",
                "version": info.get("redis_version", "unknown")
            }
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {"status": "unhealthy", "database": "redis", "error": str(e)}

    # Convenience methods for common operations
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set a value in Redis with optional expiration."""
        return await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from Redis."""
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """Check if one or more keys exist."""
        return await self.client.exists(*keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        return await self.client.expire(key, seconds)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field value."""
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None) -> int:
        """Set hash field(s)."""
        if mapping:
            return await self.client.hset(name, mapping=mapping)
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> dict:
        """Get all fields and values in a hash."""
        return await self.client.hgetall(name)

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        return await self.client.publish(channel, message)

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: float = None
    ) -> Optional[redis.lock.Lock]:
        """Acquire a distributed lock."""
        lock = self.client.lock(
            lock_name,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout
        )
        acquired = await lock.acquire()
        return lock if acquired else None

    async def release_lock(self, lock: redis.lock.Lock) -> None:
        """Release a distributed lock."""
        try:
            await lock.release()
        except redis.exceptions.LockNotOwnedError:
            logger.warning("Attempted to release a lock not owned by this client")


# Global instances (initialized on service startup)
db_manager = DatabaseManager()
redis_manager = RedisManager()


async def init_databases() -> None:
    """Initialize all database connections."""
    await asyncio.gather(
        db_manager.initialize(),
        redis_manager.initialize()
    )


async def close_databases() -> None:
    """Close all database connections."""
    await asyncio.gather(
        db_manager.close(),
        redis_manager.close()
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with db_manager.session() as session:
        yield session


def get_redis() -> redis.Redis:
    """FastAPI dependency for Redis client."""
    return redis_manager.client
