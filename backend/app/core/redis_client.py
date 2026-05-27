from __future__ import annotations

import json
import logging
from typing import Any

import redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_SECONDS = 300

redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry_on_timeout=True,
)


def build_cache_key(*parts: object) -> str:
    return ":".join(
        str(part).strip().replace(" ", "_")
        for part in parts
        if part is not None and str(part).strip() != ""
    )


def get_cache(key: str) -> Any | None:
    """Read and JSON-decode a Redis cache value.

    Redis is treated as an optimization layer. A Redis outage or invalid cached
    payload must not break API traffic, so this helper fails open and returns
    None on cache errors.
    """
    try:
        value = redis_client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except (RedisError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Redis GET failed for key %s: %s", key, exc)
        return None


def set_cache(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL_SECONDS) -> bool:
    """JSON-encode and store a Redis cache value with TTL."""
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("Redis SETEX failed for key %s: %s", key, exc)
        return False


def delete_cache(*keys: str) -> int:
    """Delete one or more Redis keys. Returns the number of deleted keys."""
    if not keys:
        return 0

    try:
        return int(redis_client.delete(*keys))
    except RedisError as exc:
        logger.warning("Redis DELETE failed for keys %s: %s", keys, exc)
        return 0


def ping_cache() -> bool:
    try:
        return bool(redis_client.ping())
    except RedisError:
        return False
