"""SQLAlchemy модели для БД"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Hand(Base):
    """Модель раздачи"""
    __tablename__ = "hands"

    id = Column(Integer, primary_key=True, index=True)
    hand_id = Column(String(100), unique=True, nullable=False, index=True)
    table_id = Column(String(100), nullable=False, index=True)
    limit_type = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    players_count = Column(Integer, nullable=False)
    hero_position = Column(Integer, nullable=False)
    hero_cards = Column(String(10), nullable=False)
    board_cards = Column(String(20))
    pot_size = Column(Numeric(10, 2), nullable=False)
    rake_amount = Column(Numeric(10, 2), nullable=False)
    hero_result = Column(Numeric(10, 2), nullable=False)
    hand_history = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class OpponentProfile(Base):
    """Модель профиля оппонента"""
    __tablename__ = "opponent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    opponent_id = Column(String(100), unique=True, nullable=False, index=True)
    table_id = Column(String(100), index=True)
    limit_type = Column(String(20))
    vpip = Column(Numeric(5, 2), default=0)
    pfr = Column(Numeric(5, 2), default=0)
    three_bet_pct = Column(Numeric(5, 2), default=0)
    aggression_factor = Column(Numeric(5, 2), default=0)
    cbet_pct = Column(Numeric(5, 2), default=0)
    fold_to_cbet_pct = Column(Numeric(5, 2), default=0)
    hands_played = Column(Integer, default=0)
    classification = Column(String(50))
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DecisionLog(Base):
    """Модель лога решений"""
    __tablename__ = "decision_log"

    id = Column(Integer, primary_key=True, index=True)
    hand_id = Column(String(100), nullable=False, index=True)
    decision_id = Column(String(100), unique=True, nullable=False)
    street = Column(String(20), nullable=False, index=True)
    game_state = Column(JSON, nullable=False)
    gto_action = Column(JSON)
    exploit_action = Column(JSON)
    final_action = Column(String(50), nullable=False)
    action_amount = Column(Numeric(10, 2))
    reasoning = Column(JSON)
    latency_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class TrainingCheckpoint(Base):
    """Модель чекпоинта обучения"""
    __tablename__ = "training_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(String(100), unique=True, nullable=False)
    version = Column(String(20), nullable=False, index=True)
    format = Column(String(20), nullable=False, index=True)
    training_iterations = Column(Integer, nullable=False)
    mccfr_config = Column(JSON)
    metrics = Column(JSON)
    file_path = Column(String(500))
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BotStats(Base):
    """Модель статистики бота"""
    __tablename__ = "bot_stats"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    limit_type = Column(String(20), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    hands_played = Column(Integer, default=0)
    vpip = Column(Numeric(5, 2), default=0)
    pfr = Column(Numeric(5, 2), default=0)
    three_bet_pct = Column(Numeric(5, 2), default=0)
    aggression_factor = Column(Numeric(5, 2), default=0)
    winrate_bb_100 = Column(Numeric(6, 2), default=0)
    total_rake = Column(Numeric(10, 2), default=0)
    rake_per_hour = Column(Numeric(10, 2), default=0)
    avg_pot_size = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
