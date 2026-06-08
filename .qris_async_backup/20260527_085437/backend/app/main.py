from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.routes import inquiry, payment, status, health

app = FastAPI(
    title="QRIS Optimization Backend",
    description="FastAPI backend for QRIS transaction optimization, legacy simulation, and monitoring readiness.",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router, tags=["Health"])
app.include_router(inquiry.router, tags=["Inquiry"])
app.include_router(payment.router, tags=["Payment"])
app.include_router(status.router, tags=["Status"])

@app.get("/")
def root():
    return {"message": "QRIS Backend Running"}