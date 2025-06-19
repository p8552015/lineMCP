from functools import lru_cache

import redis.asyncio as redis

from src.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )


async def get_cached_value(key: str) -> str | None:
    redis_client = get_redis_client()
    return await redis_client.get(key)


async def set_cached_value(
    key: str, value: str, expire_seconds: int | None = None
) -> None:
    redis_client = get_redis_client()
    await redis_client.set(key, value, ex=expire_seconds)


async def increment_counter(key: str, amount: int = 1) -> int:
    redis_client = get_redis_client()
    return await redis_client.incrby(key, amount)


async def get_counter(key: str) -> int:
    redis_client = get_redis_client()
    value = await redis_client.get(key)
    return int(value) if value else 0
