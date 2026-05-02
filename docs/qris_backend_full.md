# QRIS Backend FULL Documentation (Detailed)

---

# 1. PROJECT OVERVIEW
QRIS Optimization System backend focusing on:
- Reducing latency
- Supporting real-time transactions
- Simulating legacy system delay
- Enabling scalability via caching & async processing

---

# 2. ARCHITECTURE

Client  
↓  
FastAPI Backend (API Gateway)  
↓  
├── PostgreSQL (transactions)  
├── Redis (cache)  
├── RabbitMQ (async processing)  
└── Legacy Simulator (delay 5–10s)  

---

# 3. TRELLO TASK MAPPING

## Lukman (Backend)
- Setup FastAPI project
- Build API endpoints (inquiry, payment, status)
- Integrate DB (basic)
- Integrate Redis (optional)
- Integrate RabbitMQ
- Connect to Legacy system

## Naura
- DB schema
- Indexing
- Cache optimization

## Shean
- Async worker
- Message queue

## Dion
- Docker
- Infrastructure

## Asyam
- Monitoring (Prometheus + Grafana)

---

# 4. FULL BACKEND CODE

## main.py
```python
from fastapi import FastAPI
from routes import inquiry, payment, status

app = FastAPI()

app.include_router(inquiry.router)
app.include_router(payment.router)
app.include_router(status.router)

@app.get("/")
def root():
    return {"message": "QRIS Backend Running"}
```

---

## inquiry.py
```python
from fastapi import APIRouter
from services.legacy import call_legacy

router = APIRouter()

@router.post("/inquiry")
def inquiry():
    result = call_legacy()
    return {"source": "legacy", "data": result}
```

---

## payment.py
```python
from fastapi import APIRouter
from services.legacy import call_legacy

router = APIRouter()

@router.post("/payment")
def payment():
    result = call_legacy()
    return {"status": result["status"]}
```

---

## status.py
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/status/{id}")
def status(id: int):
    return {"id": id, "status": "SUCCESS"}
```

---

## legacy.py
```python
import time
import random

def call_legacy():
    delay = random.randint(5, 10)
    time.sleep(delay)
    return {"status": "OK"}
```

---

# 5. DOCKER SETUP

## Dockerfile
```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn sqlalchemy psycopg2-binary redis pika requests
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## docker-compose.yml
```yaml
version: "3.9"
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
```

---

# 6. TESTING

Run:
```
uvicorn main:app --reload
```

Open:
```
http://localhost:8000/docs
```

---

# 7. GITHUB WORKFLOW

```
git init
git add .
git commit -m "backend setup"
git push
```

---

# 8. NEXT STEPS

- Integrate PostgreSQL
- Add Redis caching
- Add RabbitMQ async
- Add middleware (auth, logging)
- Add monitoring

---

# 9. PRESENTATION POINTS

- Backend = API Gateway + logic handler
- Legacy system simulated with delay
- Optimization via cache & async
- Designed for scalability

---

END