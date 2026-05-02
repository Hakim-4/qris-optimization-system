-- we go boom boom 
-- dibuat naura

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- =========================
-- ENUMS
-- =========================
CREATE TYPE user_status AS ENUM (
  'ACTIVE',
  'INACTIVE',
  'BLOCKED'
);

CREATE TYPE merchant_status AS ENUM (
  'ACTIVE',
  'INACTIVE',
  'SUSPENDED'
);

CREATE TYPE transaction_status AS ENUM (
  'PENDING',
  'PROCESSING',
  'SUCCESS',
  'FAILED',
  'TIMEOUT',
  'CANCELLED'
);

CREATE TYPE transaction_type AS ENUM (
  'QRIS_INQUIRY',
  'QRIS_PAYMENT'
);

CREATE TYPE notification_status AS ENUM (
  'PENDING',
  'SENT',
  'FAILED'
);

CREATE TYPE audit_action AS ENUM (
  'CREATE',
  'UPDATE',
  'STATUS_CHANGE',
  'LEGACY_CALL',
  'CACHE_HIT',
  'CACHE_MISS',
  'RETRY'
);

-- =========================
-- USERS
-- =========================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  full_name VARCHAR(150) NOT NULL,
  phone_number VARCHAR(30) UNIQUE NOT NULL,
  email VARCHAR(150) UNIQUE,

  status user_status NOT NULL DEFAULT 'ACTIVE',

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- MERCHANTS
-- =========================

CREATE TABLE merchants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  merchant_code VARCHAR(50) UNIQUE NOT NULL,
  merchant_name VARCHAR(150) NOT NULL,
  qris_id VARCHAR(100) UNIQUE NOT NULL,

  category VARCHAR(100),
  city VARCHAR(100),

  status merchant_status NOT NULL DEFAULT 'ACTIVE',

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- TRANSACTIONS
-- =========================

CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  transaction_ref VARCHAR(100) UNIQUE NOT NULL,

  user_id UUID NOT NULL REFERENCES users(id),
  merchant_id UUID NOT NULL REFERENCES merchants(id),

  type transaction_type NOT NULL,
  status transaction_status NOT NULL DEFAULT 'PENDING',

  amount NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
  currency CHAR(3) NOT NULL DEFAULT 'IDR',

  description TEXT,

  legacy_request_id VARCHAR(100),
  legacy_response_code VARCHAR(50),
  legacy_response_message TEXT,

  request_latency_ms INTEGER,
  legacy_latency_ms INTEGER,
  db_latency_ms INTEGER,
  cache_latency_ms INTEGER,

  retry_count INTEGER NOT NULL DEFAULT 0,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- TRANSACTION LOGS
-- Async logging target
-- =========================

CREATE TABLE transaction_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,

  event_name VARCHAR(100) NOT NULL,
  message TEXT,
  metadata JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- NOTIFICATIONS
-- Async notification target
-- =========================

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),

  channel VARCHAR(50) NOT NULL DEFAULT 'PUSH',
  recipient VARCHAR(150) NOT NULL,

  title VARCHAR(150),
  message TEXT NOT NULL,

  status notification_status NOT NULL DEFAULT 'PENDING',
  sent_at TIMESTAMPTZ,
  failed_reason TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- AUDIT TRAILS
-- Async audit worker target
-- =========================

CREATE TABLE audit_trails (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
  actor_id UUID REFERENCES users(id) ON DELETE SET NULL,

  action audit_action NOT NULL,
  entity_name VARCHAR(100) NOT NULL,
  entity_id UUID,

  old_value JSONB,
  new_value JSONB,
  metadata JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- LEGACY CALL RECORDS
-- For measuring simulator behavior
-- =========================

CREATE TABLE legacy_calls (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,

  endpoint VARCHAR(150) NOT NULL,
  request_payload JSONB,
  response_payload JSONB,

  status_code INTEGER,
  latency_ms INTEGER NOT NULL,

  error_message TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- CACHE METRICS
-- For cache hit ratio measurement
-- =========================

CREATE TABLE cache_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  cache_key VARCHAR(255) NOT NULL,
  endpoint VARCHAR(150) NOT NULL,

  is_hit BOOLEAN NOT NULL,
  latency_ms INTEGER,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- API REQUEST METRICS
-- For p50, p95, p99, throughput, error rate
-- =========================

CREATE TABLE api_request_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  request_id VARCHAR(100) UNIQUE NOT NULL,

  endpoint VARCHAR(150) NOT NULL,
  method VARCHAR(10) NOT NULL,

  status_code INTEGER NOT NULL,
  latency_ms INTEGER NOT NULL,

  user_id UUID REFERENCES users(id),
  transaction_id UUID REFERENCES transactions(id),

  error_message TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- INDEXES
-- =========================

CREATE INDEX idx_users_phone_number ON users(phone_number);
CREATE INDEX idx_users_status ON users(status);

CREATE INDEX idx_merchants_qris_id ON merchants(qris_id);
CREATE INDEX idx_merchants_code ON merchants(merchant_code);
CREATE INDEX idx_merchants_status ON merchants(status);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_merchant_id ON transactions(merchant_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);
CREATE INDEX idx_transactions_user_created ON transactions(user_id, created_at DESC);
CREATE INDEX idx_transactions_merchant_created ON transactions(merchant_id, created_at DESC);

CREATE INDEX idx_transaction_logs_transaction_id ON transaction_logs(transaction_id);
CREATE INDEX idx_transaction_logs_created_at ON transaction_logs(created_at DESC);

CREATE INDEX idx_notifications_transaction_id ON notifications(transaction_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);

CREATE INDEX idx_audit_trails_transaction_id ON audit_trails(transaction_id);
CREATE INDEX idx_audit_trails_action ON audit_trails(action);
CREATE INDEX idx_audit_trails_created_at ON audit_trails(created_at DESC);

CREATE INDEX idx_legacy_calls_transaction_id ON legacy_calls(transaction_id);
CREATE INDEX idx_legacy_calls_created_at ON legacy_calls(created_at DESC);

CREATE INDEX idx_cache_metrics_endpoint_created ON cache_metrics(endpoint, created_at DESC);
CREATE INDEX idx_cache_metrics_is_hit ON cache_metrics(is_hit);

CREATE INDEX idx_api_metrics_endpoint_created ON api_request_metrics(endpoint, created_at DESC);
CREATE INDEX idx_api_metrics_latency ON api_request_metrics(latency_ms);
CREATE INDEX idx_api_metrics_created_at ON api_request_metrics(created_at DESC);
