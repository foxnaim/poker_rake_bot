-- Миграции БД для v1.2 (расширенная схема)

-- Обновление таблицы hands для v1.2
ALTER TABLE hands 
ADD COLUMN IF NOT EXISTS source VARCHAR(50),
ADD COLUMN IF NOT EXISTS players JSONB,
ADD COLUMN IF NOT EXISTS board JSONB,
ADD COLUMN IF NOT EXISTS actions JSONB,
ADD COLUMN IF NOT EXISTS result JSONB;

CREATE INDEX IF NOT EXISTS idx_hands_source ON hands(source);

-- Обновление opponent_profiles для v1.2
ALTER TABLE opponent_profiles
ADD COLUMN IF NOT EXISTS stats JSONB,
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ DEFAULT NOW();

-- Таблица для API ключей и прав доступа
CREATE TABLE IF NOT EXISTS api_keys (
    key_id SERIAL PRIMARY KEY,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    api_secret VARCHAR(255) NOT NULL,
    client_name VARCHAR(100) NOT NULL,
    permissions TEXT[] DEFAULT ARRAY['decide_only', 'log_only'],
    rate_limit_per_minute INTEGER DEFAULT 120,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Таблица для сессий (для WebSocket и контекста)
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    client_id VARCHAR(100),
    table_id VARCHAR(100),
    limit_type VARCHAR(20),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    context JSONB,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessions_client_id ON sessions(client_id);
CREATE INDEX IF NOT EXISTS idx_sessions_table_id ON sessions(table_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active);

-- Обновление decision_log для v1.2
ALTER TABLE decision_log
ADD COLUMN IF NOT EXISTS source VARCHAR(50),
ADD COLUMN IF NOT EXISTS confidence FLOAT,
ADD COLUMN IF NOT EXISTS thinking_time_ms INTEGER;

CREATE INDEX IF NOT EXISTS idx_decision_log_source ON decision_log(source);

-- Таблица для мониторинга производительности
CREATE TABLE IF NOT EXISTS performance_log (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    latency_ms INTEGER NOT NULL,
    status_code INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_performance_log_timestamp ON performance_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_log_endpoint ON performance_log(endpoint);

-- Таблица для алертов
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    is_resolved BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(is_resolved);

-- v1.3 hotfix: bot_stats.period_end должен быть nullable (NULL = активная сессия)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'bot_stats'
          AND column_name = 'period_end'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE bot_stats ALTER COLUMN period_end DROP NOT NULL;
    END IF;
END $$;

-- v1.3 hotfix: новые поля статистики (должны совпадать с data/models.py)
ALTER TABLE bot_stats
    ADD COLUMN IF NOT EXISTS rake_100 DECIMAL(6, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS profit_bb_100 DECIMAL(6, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS hands_per_hour DECIMAL(6, 2) DEFAULT 0;
