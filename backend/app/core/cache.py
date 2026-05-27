from __future__ import annotations

from typing import Any

from app.core.redis_client import build_cache_key, delete_cache, get_cache, set_cache
from app.metrics import record_cache_result

STATUS_CACHE_TTL_SECONDS = 60
IDEMPOTENCY_CACHE_TTL_SECONDS = 86_400


def read_cache(key: str) -> Any | None:
    cached = get_cache(key)
    record_cache_result(cached is not None)
    return cached


def status_cache_key(identifier: str) -> str:
    return build_cache_key("qris", "status", identifier)


def idempotency_cache_key(endpoint: str, transaction_ref: str) -> str:
    normalized_endpoint = endpoint.strip("/")
    return build_cache_key("qris", "idempotency", normalized_endpoint, transaction_ref)


def set_transaction_status_cache(
    transaction: dict[str, Any],
    ttl: int = STATUS_CACHE_TTL_SECONDS,
) -> None:
    transaction_id = transaction.get("id")
    transaction_ref = transaction.get("transaction_ref")

    if transaction_id:
        set_cache(status_cache_key(str(transaction_id)), transaction, ttl=ttl)

    if transaction_ref:
        set_cache(status_cache_key(str(transaction_ref)), transaction, ttl=ttl)


def delete_transaction_status_cache(transaction_id: str | None, transaction_ref: str | None = None) -> None:
    keys: list[str] = []
    if transaction_id:
        keys.append(status_cache_key(str(transaction_id)))
    if transaction_ref:
        keys.append(status_cache_key(str(transaction_ref)))

    if keys:
        delete_cache(*keys)
