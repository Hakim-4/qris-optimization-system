# QRIS Optimization System

## Deskripsi Proyek

QRIS Optimization System adalah backend untuk meningkatkan performa dan mendukung transaksi real-time dengan caching dan proses asinkron. Sistem ini mensimulasikan penundaan legacy system untuk pengujian.

## Fitur

* **FastAPI** sebagai API Gateway
* **Redis** untuk caching
* **RabbitMQ** untuk asynchronous processing
* **PostgreSQL** untuk penyimpanan data transaksi

## Instalasi

1. Clone repositori

```bash
git clone https://github.com/Hakim-4/qris-optimization-system.git
```

2. Setup virtual environment dan install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate # windows
pip install -r requirements.txt
```

3. Jalankan Docker

```bash
docker-compose up --build
```

## Menjalankan API

Jalankan API menggunakan FastAPI:

```bash
uvicorn main:app --reload
```

Akses di `http://localhost:8000/docs` untuk dokumentasi API.

## Struktur Direktori

```text
qris-backend/
├── backend/
│   ├── app/
│   ├── Dockerfile
│   ├── docker-compose.yml
├── requirements.txt
└── README.md
```

