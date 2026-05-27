from __future__ import annotations

import json
import logging
import time
from typing import Any

import pika
from sqlalchemy import text

from app.core.cache import set_transaction_status_cache
from app.core.config import settings
from app.core.database import SessionLocal
from app.metrics import ASYNC_PAYMENT_TOTAL, RABBITMQ_CONSUME_TOTAL
from app.services.legacy import call_legacy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [payment-worker] %(message)s",
)
logger = logging.getLogger(__name__)


def rabbitmq_parameters() -> pika.URLParameters:
    params = pika.URLParameters(settings.rabbitmq_url)
    params.heartbeat = 30
    params.blocked_connection_timeout = 10
    params.connection_attempts = 3
    params.retry_delay = 2
    return params


def connect_with_retry(max_retries: int = 30, delay_seconds: int = 2) -> pika.BlockingConnection:
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return pika.BlockingConnection(rabbitmq_parameters())
        except Exception as exc:
            last_error = exc
            logger.warning(
                "RabbitMQ is not ready yet, connection attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Could not connect to RabbitMQ") from last_error


def serialize_status(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "transaction_ref": row.transaction_ref,
        "type": row.type,
        "status": row.status,
        "amount": float(row.amount),
        "currency": row.currency,
        "description": row.description,
        "legacy_latency_ms": row.legacy_latency_ms,
        "user_name": row.user_name,
        "merchant_name": row.merchant_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def fetch_transaction_status(db, transaction_id: str):
    return db.execute(
        text(
            """
            SELECT
                t.id, t.transaction_ref, t.type::text AS type, t.status::text AS status,
                t.amount, t.currency, t.description, t.legacy_latency_ms,
                t.created_at, t.processed_at, t.completed_at,
                u.full_name AS user_name, m.merchant_name
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN merchants m ON t.merchant_id = m.id
            WHERE t.id::text = :transaction_id
            """
        ),
        {"transaction_id": transaction_id},
    ).first()


def refresh_status_cache(db, transaction_id: str) -> None:
    row = fetch_transaction_status(db, transaction_id)
    if row:
        set_transaction_status_cache(serialize_status(row))


def insert_transaction_log(
    db,
    transaction_id: str,
    event_name: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO transaction_logs (transaction_id, event_name, message, metadata)
            VALUES (:transaction_id, :event_name, :message, CAST(:metadata AS JSONB))
            """
        ),
        {
            "transaction_id": transaction_id,
            "event_name": event_name,
            "message": message,
            "metadata": json.dumps(metadata or {}, default=str),
        },
    )


def mark_processing(db, transaction_id: str) -> bool:
    row = db.execute(
        text(
            """
            UPDATE transactions
            SET status = 'PROCESSING',
                processed_at = COALESCE(processed_at, NOW()),
                updated_at = NOW()
            WHERE id::text = :transaction_id
            AND status IN ('PENDING', 'PROCESSING')
            RETURNING id
            """
        ),
        {"transaction_id": transaction_id},
    ).first()

    if not row:
        return False

    insert_transaction_log(
        db,
        transaction_id,
        "PAYMENT_PROCESSING",
        "Payment QRIS mulai diproses oleh worker RabbitMQ",
    )
    return True


def mark_failed(db, transaction_id: str, reason: str, payload: dict[str, Any] | None = None) -> None:
    db.execute(
        text(
            """
            UPDATE transactions
            SET status = 'FAILED',
                legacy_response_code = 'WORKER_ERROR',
                legacy_response_message = :reason,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id::text = :transaction_id
            AND status NOT IN ('SUCCESS', 'CANCELLED')
            """
        ),
        {"transaction_id": transaction_id, "reason": reason[:500]},
    )

    db.execute(
        text(
            """
            INSERT INTO legacy_calls (
                transaction_id,
                endpoint,
                request_payload,
                response_payload,
                status_code,
                latency_ms,
                error_message
            )
            VALUES (
                :transaction_id,
                :endpoint,
                CAST(:request_payload AS JSONB),
                CAST(:response_payload AS JSONB),
                :status_code,
                :latency_ms,
                :error_message
            )
            """
        ),
        {
            "transaction_id": transaction_id,
            "endpoint": "payment",
            "request_payload": json.dumps(payload or {}, default=str),
            "response_payload": json.dumps({"status": "FAILED", "error": reason}, default=str),
            "status_code": 500,
            "latency_ms": 0,
            "error_message": reason[:500],
        },
    )

    insert_transaction_log(
        db,
        transaction_id,
        "PAYMENT_FAILED",
        "Payment QRIS gagal diproses oleh worker RabbitMQ",
        {"reason": reason},
    )


def complete_payment(db, transaction_id: str, payload: dict[str, Any], legacy_result: dict[str, Any]) -> str:
    legacy_status_code = int(legacy_result.get("status_code", 500))
    legacy_status_message = str(legacy_result.get("status", "UNKNOWN"))
    legacy_latency_ms = int(legacy_result.get("latency_ms", 0))
    final_status = "SUCCESS" if 200 <= legacy_status_code < 300 else "FAILED"

    db.execute(
        text(
            """
            UPDATE transactions
            SET status = CAST(:status AS transaction_status),
                legacy_response_code = :legacy_response_code,
                legacy_response_message = :legacy_response_message,
                legacy_latency_ms = :legacy_latency_ms,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id::text = :transaction_id
            """
        ),
        {
            "transaction_id": transaction_id,
            "status": final_status,
            "legacy_response_code": str(legacy_status_code),
            "legacy_response_message": legacy_status_message,
            "legacy_latency_ms": legacy_latency_ms,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO legacy_calls (
                transaction_id,
                endpoint,
                request_payload,
                response_payload,
                status_code,
                latency_ms
            )
            VALUES (
                :transaction_id,
                :endpoint,
                CAST(:request_payload AS JSONB),
                CAST(:response_payload AS JSONB),
                :status_code,
                :latency_ms
            )
            """
        ),
        {
            "transaction_id": transaction_id,
            "endpoint": "payment",
            "request_payload": json.dumps(payload.get("request_payload") or payload, default=str),
            "response_payload": json.dumps(legacy_result, default=str),
            "status_code": legacy_status_code,
            "latency_ms": legacy_latency_ms,
        },
    )

    insert_transaction_log(
        db,
        transaction_id,
        "PAYMENT_SUCCESS" if final_status == "SUCCESS" else "PAYMENT_FAILED",
        "Payment QRIS berhasil diproses" if final_status == "SUCCESS" else "Payment QRIS gagal diproses legacy system",
        {"legacy_status_code": legacy_status_code, "legacy_status": legacy_status_message},
    )

    return final_status


def process_payment_job(payload: dict[str, Any]) -> None:
    transaction_id = str(payload.get("transaction_id") or "").strip()
    if not transaction_id:
        raise ValueError("RabbitMQ message does not contain transaction_id")

    db = SessionLocal()
    try:
        if not mark_processing(db, transaction_id):
            db.rollback()
            logger.info("Transaction %s is not pending or already processed", transaction_id)
            refresh_status_cache(db, transaction_id)
            return

        db.commit()
        refresh_status_cache(db, transaction_id)

        try:
            legacy_result = call_legacy(endpoint="payment")
            final_status = complete_payment(db, transaction_id, payload, legacy_result)
            db.commit()
            ASYNC_PAYMENT_TOTAL.labels(status=final_status).inc()
            refresh_status_cache(db, transaction_id)
            logger.info("Transaction %s completed with status %s", transaction_id, final_status)
        except Exception as exc:
            db.rollback()
            logger.exception("Payment processing failed for transaction %s", transaction_id)
            mark_failed(db, transaction_id, str(exc), payload)
            db.commit()
            ASYNC_PAYMENT_TOTAL.labels(status="FAILED").inc()
            refresh_status_cache(db, transaction_id)
    finally:
        db.close()


def on_message(channel, method, properties, body: bytes) -> None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Rejecting invalid JSON message: %r", body)
        RABBITMQ_CONSUME_TOTAL.labels(queue=settings.payment_queue_name, result="invalid_json").inc()
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        process_payment_job(payload)
        RABBITMQ_CONSUME_TOTAL.labels(queue=settings.payment_queue_name, result="success").inc()
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        logger.exception("Unhandled worker error: %s", exc)
        RABBITMQ_CONSUME_TOTAL.labels(queue=settings.payment_queue_name, result="failed").inc()
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main() -> None:
    while True:
        connection = None
        try:
            connection = connect_with_retry()
            channel = connection.channel()
            channel.queue_declare(queue=settings.payment_queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=settings.payment_queue_name, on_message_callback=on_message)
            logger.info("Payment worker consuming queue %s", settings.payment_queue_name)
            channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Payment worker stopped")
            if connection and connection.is_open:
                connection.close()
            return
        except Exception as exc:
            logger.exception("Payment worker connection loop failed: %s", exc)
            if connection and connection.is_open:
                connection.close()
            time.sleep(5)


if __name__ == "__main__":
    main()
