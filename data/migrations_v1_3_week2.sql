-- Миграции БД для v1.3 Week 2 - Операторка (Control-plane сущности)
-- Применение: psql -U pokerbot -d pokerbot_db -f migrations_v1_3_week2.sql

-- ============================================
-- 1. Control-plane таблицы
-- ============================================

-- Таблица ботов
CREATE TABLE IF NOT EXISTS bots (
    id SERIAL PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    default_style VARCHAR(50) NOT NULL DEFAULT 'balanced',  -- tight, balanced, loose, aggressive
    default_limit VARCHAR(20) NOT NULL DEFAULT 'NL10',  -- NL10, NL50, etc.
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bots_alias ON bots(alias);
CREATE INDEX IF NOT EXISTS idx_bots_active ON bots(active);

-- Таблица комнат
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    room_link VARCHAR(500) UNIQUE NOT NULL,  -- ссылка на комнату
    type VARCHAR(50) NOT NULL,  -- pokerstars, ggpoker, acr, etc.
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, onboarded, active, inactive
    rake_model_id INTEGER REFERENCES rake_models(id) ON DELETE SET NULL,
    meta JSONB,  -- дополнительные данные (onboarding notes, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rooms_room_link ON rooms(room_link);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);
CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(type);

-- Таблица столов
CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    limit_type VARCHAR(20) NOT NULL,  -- NL10, NL50, etc.
    max_players INTEGER NOT NULL DEFAULT 6,
    meta JSONB,  -- дополнительные данные
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(room_id, limit_type)  -- один лимит на комнату
);

CREATE INDEX IF NOT EXISTS idx_tables_room_id ON tables(room_id);
CREATE INDEX IF NOT EXISTS idx_tables_limit_type ON tables(limit_type);

-- Таблица моделей рейка
CREATE TABLE IF NOT EXISTS rake_models (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES rooms(id) ON DELETE CASCADE,
    limit_type VARCHAR(20),  -- NULL = для всех лимитов комнаты
    percent DECIMAL(5, 2) NOT NULL,  -- процент рейка (например, 5.00)
    cap DECIMAL(10, 2),  -- максимальный рейк (например, 3.00)
    min_pot DECIMAL(10, 2) DEFAULT 0,  -- минимальный пот для рейка
    params JSONB,  -- дополнительные параметры модели
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(room_id, limit_type)  -- одна модель на room+limit
);

CREATE INDEX IF NOT EXISTS idx_rake_models_room_id ON rake_models(room_id);
CREATE INDEX IF NOT EXISTS idx_rake_models_limit_type ON rake_models(limit_type);

-- Таблица конфигураций ботов
CREATE TABLE IF NOT EXISTS bot_configs (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER REFERENCES bots(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- название конфига
    target_vpip DECIMAL(5, 2) NOT NULL DEFAULT 20.0,  -- целевой VPIP
    target_pfr DECIMAL(5, 2) NOT NULL DEFAULT 15.0,  -- целевой PFR
    target_af DECIMAL(5, 2) NOT NULL DEFAULT 2.0,  -- целевой Aggression Factor
    exploit_weights JSONB NOT NULL DEFAULT '{"preflop": 0.3, "flop": 0.4, "turn": 0.5, "river": 0.6}'::jsonb,  -- веса exploit по улицам
    max_winrate_cap DECIMAL(6, 2),  -- максимальный винрейт (bb/100), NULL = без ограничений
    anti_pattern_params JSONB,  -- параметры anti-pattern роутера
    limit_types TEXT[],  -- для каких лимитов применима (NULL = все)
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_configs_bot_id ON bot_configs(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_configs_is_default ON bot_configs(is_default);

-- Таблица сессий ботов
CREATE TABLE IF NOT EXISTS bot_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    bot_id INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    table_id INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    bot_config_id INTEGER REFERENCES bot_configs(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'starting',  -- starting, running, paused, stopped, error
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    hands_played INTEGER DEFAULT 0,
    profit DECIMAL(10, 2) DEFAULT 0,  -- прибыль в долларах
    rake_paid DECIMAL(10, 2) DEFAULT 0,  -- уплаченный рейк
    bb_100 DECIMAL(6, 2) DEFAULT 0,  -- винрейт в bb/100
    rake_100 DECIMAL(6, 2) DEFAULT 0,  -- рейк в bb/100
    last_error TEXT,  -- последняя ошибка (если status = error)
    meta JSONB,  -- дополнительные данные сессии
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_sessions_session_id ON bot_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_bot_id ON bot_sessions(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_table_id ON bot_sessions(table_id);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_status ON bot_sessions(status);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_started_at ON bot_sessions(started_at);

-- Таблица агентов (физические экземпляры ботов)
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,  -- уникальный ID агента
    status VARCHAR(20) NOT NULL DEFAULT 'offline',  -- online, offline, error
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    version VARCHAR(50),  -- версия агента
    assigned_session_id INTEGER REFERENCES bot_sessions(id) ON DELETE SET NULL,
    meta JSONB,  -- дополнительные данные агента
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_assigned_session_id ON agents(assigned_session_id);

-- Таблица аудита (кто/что/когда изменил)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),  -- кто (API key, user, system)
    action VARCHAR(50) NOT NULL,  -- что (create, update, delete, start_session, etc.)
    entity_type VARCHAR(50) NOT NULL,  -- тип сущности (bot, room, table, session, etc.)
    entity_id INTEGER,  -- ID сущности
    old_values JSONB,  -- старые значения (для update)
    new_values JSONB,  -- новые значения
    metadata JSONB,  -- дополнительные данные
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- ============================================
-- 2. Обновление существующих таблиц (привязка к session_id)
-- ============================================

-- Добавляем session_id в hands
ALTER TABLE hands 
ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES bot_sessions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_hands_session_id ON hands(session_id);

-- Добавляем session_id в decision_log
ALTER TABLE decision_log
ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES bot_sessions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_decision_log_session_id ON decision_log(session_id);

-- Обновляем bot_stats для совместимости (session_id уже есть, но убедимся что он правильный)
-- bot_stats.session_id уже существует, но проверим что он ссылается на bot_sessions
-- Если нужно, можно добавить foreign key позже

-- ============================================
-- 3. Обновление api_keys для permissions
-- ============================================

-- Добавляем поле admin если его нет
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_api_keys_is_admin ON api_keys(is_admin);

-- Обновляем permissions для поддержки admin прав
-- permissions уже TEXT[], можно добавить 'admin' в массив

-- ============================================
-- 4. Триггеры для updated_at
-- ============================================

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Применяем триггеры к таблицам
DROP TRIGGER IF EXISTS update_bots_updated_at ON bots;
CREATE TRIGGER update_bots_updated_at BEFORE UPDATE ON bots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_rooms_updated_at ON rooms;
CREATE TRIGGER update_rooms_updated_at BEFORE UPDATE ON rooms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tables_updated_at ON tables;
CREATE TRIGGER update_tables_updated_at BEFORE UPDATE ON tables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_rake_models_updated_at ON rake_models;
CREATE TRIGGER update_rake_models_updated_at BEFORE UPDATE ON rake_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bot_configs_updated_at ON bot_configs;
CREATE TRIGGER update_bot_configs_updated_at BEFORE UPDATE ON bot_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bot_sessions_updated_at ON bot_sessions;
CREATE TRIGGER update_bot_sessions_updated_at BEFORE UPDATE ON bot_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. Начальные данные (опционально)
-- ============================================

-- Создаем дефолтного бота
INSERT INTO bots (alias, default_style, default_limit, active)
VALUES ('default_bot', 'balanced', 'NL10', TRUE)
ON CONFLICT (alias) DO NOTHING;

-- Создаем дефолтный admin API key (если нужно)
-- ВАЖНО: В продакшене это должно быть сделано через API или вручную!
-- INSERT INTO api_keys (api_key, api_secret, client_name, permissions, is_admin, is_active)
-- VALUES ('admin_key_here', 'secret_here', 'admin', ARRAY['admin'], TRUE, TRUE)
-- ON CONFLICT (api_key) DO NOTHING;
