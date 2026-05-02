import random
import time
from datetime import datetime, timezone


def call_legacy(endpoint: str = "legacy"):
    """Simulate slow legacy QRIS service with 5 to 10 seconds delay."""
    delay_seconds = random.randint(5, 10)
    started_at = datetime.now(timezone.utc)
    time.sleep(delay_seconds)
    latency_ms = delay_seconds * 1000

    return {
        "endpoint": endpoint,
        "status": "OK",
        "status_code": 200,
        "latency_ms": latency_ms,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
