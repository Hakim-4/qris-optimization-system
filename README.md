# QRIS Optimization Backend

Backend QRIS berbasis FastAPI untuk simulasi transaksi, pengujian latency, integrasi database PostgreSQL, Redis, RabbitMQ, dan simulasi sistem legacy.

## Fitur Utama

- FastAPI sebagai API Gateway
- Endpoint inquiry, payment, dan status transaksi
- Simulasi legacy system dengan delay 5 sampai 10 detik
- PostgreSQL schema melalui `database/init.sql`
- Redis siap digunakan untuk caching
- RabbitMQ siap digunakan untuk async processing
- Docker Compose untuk menjalankan service lokal

## Struktur Project

```text
qris-backend-github-ready/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── inquiry.py
│   │   │   ├── payment.py
│   │   │   └── status.py
│   │   ├── services/
│   │   │   └── legacy.py
│   │   └── core/
│   │       └── config.py
│   ├── Dockerfile
│   └── requirements.txt
├── database/
│   └── init.sql
├── docs/
│   └── qris_backend_full.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Cara Menjalankan Lokal dengan Docker

Salin file environment:

```bash
cp .env.example .env
```

Jalankan semua service:

```bash
docker compose up --build
```

Buka dokumentasi API:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

## Endpoint Utama

### Root

```http
GET /
```

### Health Check

```http
GET /health
```

### QRIS Inquiry

```http
POST /inquiry
```

### QRIS Payment

```http
POST /payment
```

### Transaction Status

```http
GET /status/{transaction_id}
```

## Cara Push ke GitHub

Buat repository baru di GitHub. Jangan centang `Add README`, karena README sudah tersedia di project ini.

Lalu jalankan command berikut dari folder project:

```bash
git init
git add .
git commit -m "Initial QRIS backend setup"
git branch -M main
git remote add origin https://github.com/USERNAME/NAMA-REPOSITORY.git
git push -u origin main
```

Ganti `USERNAME` dan `NAMA-REPOSITORY` sesuai akun GitHub kamu.

## Catatan Penting

Jangan upload file `.env` ke GitHub. Gunakan `.env.example` sebagai contoh konfigurasi.
