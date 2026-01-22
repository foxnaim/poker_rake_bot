"""SQLAlchemy модели для БД"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, JSON, ForeignKey, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
    session_id = Column(Integer, ForeignKey("bot_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
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
    
    # Relationships
    session = relationship("BotSession", back_populates="hands")


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
    session_id = Column(Integer, ForeignKey("bot_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    street = Column(String(20), nullable=False, index=True)
    game_state = Column(JSON, nullable=False)
    gto_action = Column(JSON)
    exploit_action = Column(JSON)
    final_action = Column(String(50), nullable=False)
    action_amount = Column(Numeric(10, 2))
    reasoning = Column(JSON)
    latency_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("BotSession", back_populates="decisions")


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
    period_end = Column(DateTime, nullable=True)  # null = active session
    hands_played = Column(Integer, default=0)
    vpip = Column(Numeric(5, 2), default=0)
    pfr = Column(Numeric(5, 2), default=0)
    three_bet_pct = Column(Numeric(5, 2), default=0)
    aggression_factor = Column(Numeric(5, 2), default=0)
    winrate_bb_100 = Column(Numeric(6, 2), default=0)
    total_rake = Column(Numeric(10, 2), default=0)
    rake_per_hour = Column(Numeric(10, 2), default=0)
    rake_100 = Column(Numeric(6, 2), default=0)  # Rake per 100 hands
    profit_bb_100 = Column(Numeric(6, 2), default=0)  # Profit in bb/100
    hands_per_hour = Column(Numeric(6, 2), default=0)  # Hands per hour
    avg_pot_size = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# Week 2: Control-plane модели
# ============================================

class Bot(Base):
    """Модель бота"""
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String(100), unique=True, nullable=False, index=True)
    default_style = Column(String(50), nullable=False, default="balanced")
    default_limit = Column(String(20), nullable=False, default="NL10")
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    configs = relationship("BotConfig", back_populates="bot", cascade="all, delete-orphan")
    sessions = relationship("BotSession", back_populates="bot", cascade="all, delete-orphan")


class Room(Base):
    """Модель комнаты"""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_link = Column(String(500), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    rake_model_id = Column(Integer, ForeignKey("rake_models.id", ondelete="SET NULL"), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tables = relationship("Table", back_populates="room", cascade="all, delete-orphan")
    # Важно: есть ДВЕ связи rooms <-> rake_models:
    # 1) rooms.rake_model_id -> rake_models.id (дефолтная модель рейка комнаты)
    # 2) rake_models.room_id -> rooms.id (список моделей рейка, в т.ч. per-limit)
    # Поэтому явно указываем foreign_keys чтобы избежать неоднозначности маппинга.
    default_rake_model = relationship(
        "RakeModel",
        foreign_keys=[rake_model_id],
        post_update=True,
    )
    rake_models_rel = relationship(
        "RakeModel",
        back_populates="room",
        cascade="all, delete-orphan",
        foreign_keys="RakeModel.room_id",
    )


class Table(Base):
    """Модель стола"""
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    # Внешний ID стола (как его видит агент/логика: "table_1", "pp_123", etc.)
    external_table_id = Column(String(100), nullable=True, index=True)
    limit_type = Column(String(20), nullable=False, index=True)
    max_players = Column(Integer, nullable=False, default=6)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    room = relationship("Room", back_populates="tables")
    sessions = relationship("BotSession", back_populates="table", cascade="all, delete-orphan")

    @property
    def table_key(self) -> Optional[str]:
        """
        Человеко/agent-friendly идентификатор стола для UI.
        (Храним в БД как external_table_id, чтобы не путать с PK id.)
        """
        return self.external_table_id


class RakeModel(Base):
    """Модель рейка"""
    __tablename__ = "rake_models"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True, index=True)
    limit_type = Column(String(20), nullable=True, index=True)
    percent = Column(Numeric(5, 2), nullable=False)
    cap = Column(Numeric(10, 2), nullable=True)
    min_pot = Column(Numeric(10, 2), nullable=True, default=0)
    params = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    room = relationship(
        "Room",
        back_populates="rake_models_rel",
        foreign_keys=[room_id],
    )


class BotConfig(Base):
    """Модель конфигурации бота"""
    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_vpip = Column(Numeric(5, 2), nullable=False, default=20.0)
    target_pfr = Column(Numeric(5, 2), nullable=False, default=15.0)
    target_af = Column(Numeric(5, 2), nullable=False, default=2.0)
    exploit_weights = Column(JSON, nullable=False, default={"preflop": 0.3, "flop": 0.4, "turn": 0.5, "river": 0.6})
    max_winrate_cap = Column(Numeric(6, 2), nullable=True)
    anti_pattern_params = Column(JSON, nullable=True)
    # ARRAY в Postgres, JSON в sqlite (для локального режима "без докера"/тестов).
    limit_types = Column(ARRAY(String).with_variant(JSON, "sqlite"), nullable=True)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="configs")
    sessions = relationship("BotSession", back_populates="bot_config")


class BotSession(Base):
    """Модель сессии бота"""
    __tablename__ = "bot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True)
    bot_config_id = Column(Integer, ForeignKey("bot_configs.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="starting", index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    hands_played = Column(Integer, default=0)
    profit = Column(Numeric(10, 2), default=0)
    rake_paid = Column(Numeric(10, 2), default=0)
    bb_100 = Column(Numeric(6, 2), default=0)
    rake_100 = Column(Numeric(6, 2), default=0)
    last_error = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="sessions")
    table = relationship("Table", back_populates="sessions")
    bot_config = relationship("BotConfig", back_populates="sessions")
    hands = relationship("Hand", back_populates="session")
    decisions = relationship("DecisionLog", back_populates="session")
    agents = relationship("Agent", back_populates="assigned_session")

    @property
    def table_key(self) -> Optional[str]:
        """
        Human/agent-friendly идентификатор стола для UI.
        Берём из связанного Table.external_table_id.
        """
        try:
            return self.table.external_table_id if self.table is not None else None
        except Exception:
            return None


class Agent(Base):
    """Модель агента (физический экземпляр бота)"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="offline", index=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    version = Column(String(50), nullable=True)
    assigned_session_id = Column(Integer, ForeignKey("bot_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assigned_session = relationship("BotSession", back_populates="agents")


class APIKey(Base):
    """API ключи для аутентификации агентов"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    permissions = Column(JSON, nullable=False, default=list)  # ['agent', 'read', 'write', 'admin']
    is_active = Column(Boolean, default=True, index=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Модель аудита"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    # 'metadata' зарезервировано в SQLAlchemy Declarative API
    meta_data = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
