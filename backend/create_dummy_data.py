from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from models.user import User
from models.transaction import Transaction
from models.merchant import Merchant  # pastikan model Merchant ada
import uuid

# Buat semua table jika belum ada
from app.core.database import Base
Base.metadata.create_all(bind=engine)

# Fungsi untuk generate dummy user & merchant
def create_dummy_data():
    db: Session = SessionLocal()
    try:
        # Tambah user dummy
        user_id = str(uuid.uuid4())
        user = User(id=user_id, name="Lukman", email="lukman@example.com", status="active")
        db.add(user)
        
        # Tambah merchant dummy
        merchant_id = str(uuid.uuid4())
        merchant = Merchant(id=merchant_id, name="Merchant A", category="Food", status="active")
        db.add(merchant)

        # Commit data
        db.commit()
        print(f"Dummy user id: {user_id}")
        print(f"Dummy merchant id: {merchant_id}")
    finally:
        db.close()

if __name__ == "__main__":
    create_dummy_data()