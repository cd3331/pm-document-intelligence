"""
Redis Cache Management for PM Document Intelligence.

This module handles Redis connections, caching operations, and cache management
for the application.

Features:
- Connection pooling
- Async Redis operations
- Cache key management
- TTL-based expiration
- Health checks

Usage:
    from app.cache.redis import get_cache, set_cache, delete_cache

    # Set cache
    await set_cache("user:123", user_data, ttl=3600)

    # Get cache
    user_data = await get_cache("user:123")

    # Delete cache
    await delete_cache("user:123")
"""

import json
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Global Redis client
_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """
    Get or create Redis client.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            # Parse Redis URL
            redis_url = str(settings.redis.redis_url)

            # Create Redis client
            _redis_client = await aioredis.from_url(
                redis_url,
                password=settings.redis.redis_password,
                max_connections=settings.redis.redis_max_connections,
                socket_timeout=settings.redis.redis_socket_timeout,
                socket_connect_timeout=settings.redis.redis_socket_connect_timeout,
                decode_responses=True,
                encoding="utf-8",
            )

            logger.info(f"Redis client created: {redis_url}")

        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}", exc_info=True)
            raise

    return _redis_client


async def test_redis_connection() -> bool:
    """
    Test Redis connectivity.

    Returns:
        True if connection successful, False otherwise
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        logger.debug("Redis not enabled, skipping connection test")
        return False

    try:
        client = await get_redis_client()
        await client.ping()
        logger.debug("Redis connection test successful")
        return True

    except Exception as e:
        logger.error(f"Redis connection test failed: {e}", exc_info=True)
        return False


async def initialize_cache() -> None:
    """
    Initialize cache on application startup.
    """
    if not settings.cache.cache_enabled:
        logger.info("Caching disabled, skipping initialization")
        return

    try:
        client = await get_redis_client()
        await client.ping()
        logger.info("Cache initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}", exc_info=True)


async def close_redis_connections() -> None:
    """
    Close Redis connections.

    Called during application shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        logger.info("Redis connections closed")
        _redis_client = None


def _build_cache_key(key: str, prefix: str | None = None) -> str:
    """
    Build cache key with optional prefix.

    Args:
        key: Base cache key
        prefix: Optional prefix

    Returns:
        Full cache key
    """
    if prefix:
        return f"{prefix}:{key}"
    return f"{settings.app_name}:{key}"


async def get_cache(
    key: str,
    prefix: str | None = None,
    deserialize: bool = True,
) -> Any | None:
    """
    Get value from cache.

    Args:
        key: Cache key
        prefix: Optional key prefix
        deserialize: Deserialize JSON if True

    Returns:
        Cached value or None if not found
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return None

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        value = await client.get(cache_key)

        if value is None:
            return None

        if deserialize:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to deserialize cache value for key: {cache_key}")
                return value

        return value

    except RedisError as e:
        logger.error(f"Redis error getting cache for key {key}: {e}", exc_info=True)
        return None


async def set_cache(
    key: str,
    value: Any,
    ttl: int | None = None,
    prefix: str | None = None,
    serialize: bool = True,
) -> bool:
    """
    Set value in cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (uses default if None)
        prefix: Optional key prefix
        serialize: Serialize to JSON if True

    Returns:
        True if successful, False otherwise
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return False

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        # Serialize value if needed
        if serialize:
            value = json.dumps(value)

        # Use default TTL if not specified
        if ttl is None:
            ttl = settings.cache.cache_default_ttl

        # Set with TTL
        await client.setex(cache_key, ttl, value)

        logger.debug(f"Cache set for key: {cache_key} (TTL: {ttl}s)")
        return True

    except RedisError as e:
        logger.error(f"Redis error setting cache for key {key}: {e}", exc_info=True)
        return False


async def delete_cache(
    key: str,
    prefix: str | None = None,
) -> bool:
    """
    Delete value from cache.

    Args:
        key: Cache key
        prefix: Optional key prefix

    Returns:
        True if successful, False otherwise
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return False

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        await client.delete(cache_key)

        logger.debug(f"Cache deleted for key: {cache_key}")
        return True

    except RedisError as e:
        logger.error(f"Redis error deleting cache for key {key}: {e}", exc_info=True)
        return False


async def clear_cache_pattern(
    pattern: str,
    prefix: str | None = None,
) -> int:
    """
    Clear cache keys matching pattern.

    Args:
        pattern: Key pattern (supports wildcards)
        prefix: Optional key prefix

    Returns:
        Number of keys deleted
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return 0

    try:
        client = await get_redis_client()
        cache_pattern = _build_cache_key(pattern, prefix)

        # Find matching keys
        keys = []
        async for key in client.scan_iter(match=cache_pattern):
            keys.append(key)

        # Delete keys
        if keys:
            deleted = await client.delete(*keys)
            logger.info(f"Deleted {deleted} cache keys matching pattern: {cache_pattern}")
            return deleted

        return 0

    except RedisError as e:
        logger.error(f"Redis error clearing cache pattern {pattern}: {e}", exc_info=True)
        return 0


async def exists_cache(
    key: str,
    prefix: str | None = None,
) -> bool:
    """
    Check if cache key exists.

    Args:
        key: Cache key
        prefix: Optional key prefix

    Returns:
        True if key exists, False otherwise
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return False

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        return await client.exists(cache_key) > 0

    except RedisError as e:
        logger.error(f"Redis error checking cache existence for key {key}: {e}", exc_info=True)
        return False


async def get_cache_ttl(
    key: str,
    prefix: str | None = None,
) -> int | None:
    """
    Get remaining TTL for cache key.

    Args:
        key: Cache key
        prefix: Optional key prefix

    Returns:
        TTL in seconds or None if key doesn't exist
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return None

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        ttl = await client.ttl(cache_key)

        if ttl == -2:  # Key doesn't exist
            return None
        elif ttl == -1:  # Key exists but has no expiration
            return -1

        return ttl

    except RedisError as e:
        logger.error(f"Redis error getting TTL for key {key}: {e}", exc_info=True)
        return None


async def increment_cache(
    key: str,
    amount: int = 1,
    prefix: str | None = None,
    ttl: int | None = None,
) -> int | None:
    """
    Increment cache value (for counters).

    Args:
        key: Cache key
        amount: Amount to increment by
        prefix: Optional key prefix
        ttl: TTL for the key if it doesn't exist

    Returns:
        New value after increment, or None on error
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return None

    try:
        client = await get_redis_client()
        cache_key = _build_cache_key(key, prefix)

        # Increment
        new_value = await client.incrby(cache_key, amount)

        # Set TTL if key is new
        if ttl and new_value == amount:
            await client.expire(cache_key, ttl)

        return new_value

    except RedisError as e:
        logger.error(f"Redis error incrementing cache for key {key}: {e}", exc_info=True)
        return None


async def get_cache_stats() -> dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache stats
    """
    if not settings.cache.cache_enabled or settings.cache.cache_type != "redis":
        return {"enabled": False}

    try:
        client = await get_redis_client()

        # Get Redis info
        info = await client.info()

        return {
            "enabled": True,
            "type": "redis",
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
        }

    except RedisError as e:
        logger.error(f"Redis error getting stats: {e}", exc_info=True)
        return {"enabled": True, "error": str(e)}
