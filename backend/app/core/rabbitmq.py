from __future__ import annotations

import json
import logging
from typing import Any

import pika
from app.core.config import settings
from app.metrics import RABBITMQ_PUBLISH_TOTAL

logger = logging.getLogger(__name__)


def _rabbitmq_parameters() -> pika.URLParameters:
    params = pika.URLParameters(settings.rabbitmq_url)
    params.heartbeat = 30
    params.blocked_connection_timeout = 5
    params.connection_attempts = 3
    params.retry_delay = 2
    return params


def _connect() -> pika.BlockingConnection:
    return pika.BlockingConnection(_rabbitmq_parameters())


def publish_message(queue_name: str, payload: dict[str, Any]) -> bool:
    """Publish a durable JSON message to RabbitMQ.

    The API treats RabbitMQ as required infrastructure for async payment. If the
    publish fails, the caller should mark the payment as FAILED instead of
    pretending the job was accepted.
    """
    connection: pika.BlockingConnection | None = None
    try:
        connection = _connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(payload, default=str).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
            mandatory=True,
        )
        RABBITMQ_PUBLISH_TOTAL.labels(queue=queue_name, result="success").inc()
        return True
    except Exception as exc:
        RABBITMQ_PUBLISH_TOTAL.labels(queue=queue_name, result="failed").inc()
        logger.exception("RabbitMQ publish failed for queue %s: %s", queue_name, exc)
        return False
    finally:
        if connection and connection.is_open:
            connection.close()


def publish_payment_job(payload: dict[str, Any]) -> bool:
    return publish_message(settings.payment_queue_name, payload)
