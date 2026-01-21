-- Миграция Week 3: Добавление полей rake_100, profit_bb_100, hands_per_hour в bot_stats

-- Добавляем новые поля в bot_stats
ALTER TABLE bot_stats 
ADD COLUMN IF NOT EXISTS rake_100 DECIMAL(6, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS profit_bb_100 DECIMAL(6, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS hands_per_hour DECIMAL(6, 2) DEFAULT 0;

-- Комментарии для документации
COMMENT ON COLUMN bot_stats.rake_100 IS 'Rake per 100 hands';
COMMENT ON COLUMN bot_stats.profit_bb_100 IS 'Profit in big blinds per 100 hands';
COMMENT ON COLUMN bot_stats.hands_per_hour IS 'Average hands per hour';
