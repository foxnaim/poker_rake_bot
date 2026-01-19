-- Инициализация схемы БД для Poker Rake Bot

-- Таблица для хранения раздач
CREATE TABLE IF NOT EXISTS hands (
    id SERIAL PRIMARY KEY,
    hand_id VARCHAR(100) UNIQUE NOT NULL,
    table_id VARCHAR(100) NOT NULL,
    limit_type VARCHAR(20) NOT NULL,  -- NL10, NL50, etc.
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    players_count INTEGER NOT NULL,
    hero_position INTEGER NOT NULL,
    hero_cards VARCHAR(10) NOT NULL,  -- e.g., "AsKh"
    board_cards VARCHAR(20),  -- e.g., "2c3d4h" (flop), "2c3d4h5s" (turn), "2c3d4h5s6c" (river)
    pot_size DECIMAL(10, 2) NOT NULL,
    rake_amount DECIMAL(10, 2) NOT NULL,
    hero_result DECIMAL(10, 2) NOT NULL,  -- выигрыш/проигрыш
    hand_history JSONB,  -- полная история раздачи
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_hands_table_id ON hands(table_id);
CREATE INDEX idx_hands_timestamp ON hands(timestamp);
CREATE INDEX idx_hands_limit_type ON hands(limit_type);

-- Таблица для профилей оппонентов
CREATE TABLE IF NOT EXISTS opponent_profiles (
    id SERIAL PRIMARY KEY,
    opponent_id VARCHAR(100) UNIQUE NOT NULL,
    table_id VARCHAR(100),
    limit_type VARCHAR(20),
    vpip DECIMAL(5, 2) DEFAULT 0,  -- Voluntarily Put $ In Pot
    pfr DECIMAL(5, 2) DEFAULT 0,  -- Pre-Flop Raise
    three_bet_pct DECIMAL(5, 2) DEFAULT 0,
    aggression_factor DECIMAL(5, 2) DEFAULT 0,
    cbet_pct DECIMAL(5, 2) DEFAULT 0,  -- continuation bet %
    fold_to_cbet_pct DECIMAL(5, 2) DEFAULT 0,
    hands_played INTEGER DEFAULT 0,
    classification VARCHAR(50),  -- fish_loose, nit, tag, lag, calling_station
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_opponent_profiles_opponent_id ON opponent_profiles(opponent_id);
CREATE INDEX idx_opponent_profiles_table_id ON opponent_profiles(table_id);

-- Таблица для логов решений бота
CREATE TABLE IF NOT EXISTS decision_log (
    id SERIAL PRIMARY KEY,
    hand_id VARCHAR(100) NOT NULL,
    decision_id VARCHAR(100) UNIQUE NOT NULL,
    street VARCHAR(20) NOT NULL,  -- preflop, flop, turn, river
    game_state JSONB NOT NULL,  -- состояние игры на момент решения
    gto_action JSONB,  -- GTO решение от MCCFR
    exploit_action JSONB,  -- эксплойт-коррекция
    final_action VARCHAR(50) NOT NULL,  -- финальное действие (fold, call, raise, check)
    action_amount DECIMAL(10, 2),
    reasoning JSONB,  -- объяснение решения
    latency_ms INTEGER,  -- время ответа в миллисекундах
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decision_log_hand_id ON decision_log(hand_id);
CREATE INDEX idx_decision_log_timestamp ON decision_log(timestamp);
CREATE INDEX idx_decision_log_street ON decision_log(street);

-- Таблица для чекпоинтов обучения
CREATE TABLE IF NOT EXISTS training_checkpoints (
    id SERIAL PRIMARY KEY,
    checkpoint_id VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    format VARCHAR(20) NOT NULL,  -- NL10, NL50, etc.
    training_iterations INTEGER NOT NULL,
    mccfr_config JSONB,  -- конфигурация MCCFR
    metrics JSONB,  -- метрики обучения (regret, exploitability, etc.)
    file_path VARCHAR(500),  -- путь к файлу чекпоинта
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_training_checkpoints_version ON training_checkpoints(version);
CREATE INDEX idx_training_checkpoints_format ON training_checkpoints(format);
CREATE INDEX idx_training_checkpoints_active ON training_checkpoints(is_active);

-- Таблица для статистики бота
CREATE TABLE IF NOT EXISTS bot_stats (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    limit_type VARCHAR(20) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    hands_played INTEGER DEFAULT 0,
    vpip DECIMAL(5, 2) DEFAULT 0,
    pfr DECIMAL(5, 2) DEFAULT 0,
    three_bet_pct DECIMAL(5, 2) DEFAULT 0,
    aggression_factor DECIMAL(5, 2) DEFAULT 0,
    winrate_bb_100 DECIMAL(6, 2) DEFAULT 0,
    total_rake DECIMAL(10, 2) DEFAULT 0,
    rake_per_hour DECIMAL(10, 2) DEFAULT 0,
    avg_pot_size DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bot_stats_session_id ON bot_stats(session_id);
CREATE INDEX idx_bot_stats_limit_type ON bot_stats(limit_type);
CREATE INDEX idx_bot_stats_period ON bot_stats(period_start, period_end);
