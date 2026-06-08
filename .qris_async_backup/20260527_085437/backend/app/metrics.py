from prometheus_client import Counter, Histogram, Gauge

TRANSACTION_TOTAL = Counter(
    "qris_transactions_total",
    "Total number of QRIS transactions",
    ["status", "payment_method"]
)

TRANSACTION_AMOUNT = Histogram(
    "qris_transaction_amount_rupiah",
    "Transaction amount in Rupiah",
    buckets=[10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000, 5_000_000]
)

LEGACY_LATENCY = Histogram(
    "qris_legacy_latency_seconds",
    "Legacy system response time in seconds",
    buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0]
)

CACHE_HITS = Counter(
    "qris_cache_hits_total",
    "Total Redis cache hits"
)

CACHE_MISSES = Counter(
    "qris_cache_misses_total",
    "Total Redis cache misses"
)

CACHE_HIT_RATIO = Gauge(
    "qris_cache_hit_ratio",
    "Current cache hit ratio (0.0 - 1.0)"
)

API_ERRORS = Counter(
    "qris_api_errors_total",
    "Total API errors",
    ["endpoint", "error_code"]
)