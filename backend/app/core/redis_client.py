# app/core/redis_client.py
import redis
import json
from app.core.config import settings

redis_client = redis.from_url(settings.redis_url)

def get_cache(key: str):
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def set_cache(key: str, value, ttl=300):
    redis_client.setex(key, ttl, json.dumps(value))