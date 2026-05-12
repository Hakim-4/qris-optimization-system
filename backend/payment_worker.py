import pika
import json
from app.core.database import SessionLocal
from app.models.transaction import Transaction

from app.core.config import settings

def callback(ch, method, properties, body):
    """
    Fungsi untuk memproses task dari queue RabbitMQ.
    Mengupdate status transaksi di database.
    """
    data = json.loads(body)
    transaction_id = data["transaction_id"]

    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.status = "paid"  # contoh update status
            db.commit()
            print(f"Transaction {transaction_id} updated to 'paid'")
        else:
            print(f"Transaction {transaction_id} not found")
    finally:
        db.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    # Connect ke RabbitMQ
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Pastikan queue ada
    channel.queue_declare(queue="payment_queue", durable=True)

    # Batasi prefetch supaya worker tidak overload
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="payment_queue", on_message_callback=callback)

    print("Payment worker started. Waiting for messages...")
    channel.start_consuming()

if __name__ == "__main__":
    main()