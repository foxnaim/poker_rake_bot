"""Pydantic схемы для API"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class GameStateRequest(BaseModel):
    """Запрос состояния игры для принятия решения"""
    hand_id: str
    table_id: str
    limit_type: str = Field(default="NL10", description="Лимит игры (NL10, NL50)")
    session_id: Optional[str] = Field(None, description="ID сессии бота (для привязки к session)")
    street: str = Field(description="Улица: preflop, flop, turn, river")
    hero_position: int = Field(description="Позиция героя (0-5)")
    dealer: int = Field(description="Позиция дилера (0-5)")
    hero_cards: str = Field(description="Карты героя (например, 'AsKh')")
    board_cards: Optional[str] = Field(default="", description="Карты на борде")
    stacks: Dict[str, float] = Field(description="Стеки игроков {player_id: stack}")
    bets: Dict[str, float] = Field(description="Ставки в текущем раунде")
    total_bets: Dict[str, float] = Field(description="Общие ставки игроков")
    active_players: List[int] = Field(description="Активные игроки")
    pot: float = Field(description="Размер пота")
    current_player: int = Field(description="Текущий игрок")
    last_raise_amount: float = Field(default=0.0, description="Размер последнего рейза")
    small_blind: float = Field(default=0.5)
    big_blind: float = Field(default=1.0)
    opponent_ids: Optional[List[str]] = Field(default=None, description="ID оппонентов")


class DecisionResponse(BaseModel):
    """Ответ с решением бота"""
    action: str = Field(description="Действие: fold, check, call, raise, all_in")
    amount: Optional[float] = Field(default=None, description="Размер ставки (для raise)")
    reasoning: Optional[Dict] = Field(default=None, description="Объяснение решения")
    latency_ms: int = Field(default=0, description="Время ответа в миллисекундах")
    cached: Optional[bool] = Field(default=False, description="Было ли решение из кэша")


class HandLogRequest(BaseModel):
    """Запрос для логирования раздачи"""
    hand_id: str
    table_id: str
    limit_type: str
    session_id: Optional[str] = Field(None, description="ID сессии бота (для привязки к session)")
    players_count: int
    hero_position: int
    hero_cards: str
    board_cards: Optional[str] = ""
    pot_size: float
    rake_amount: float
    hero_result: float
    hand_history: Optional[Dict] = None


class OpponentProfileResponse(BaseModel):
    """Профиль оппонента"""
    opponent_id: str
    vpip: float
    pfr: float
    three_bet_pct: float
    aggression_factor: float
    hands_played: int
    classification: str


class OpponentProfileCreate(BaseModel):
    """Создание профиля оппонента"""
    opponent_id: str = Field(description="ID оппонента")
    vpip: float = Field(ge=0, le=100, description="VPIP (0-100)")
    pfr: float = Field(ge=0, le=100, description="PFR (0-100)")
    three_bet_pct: float = Field(ge=0, le=100, description="3-bet% (0-100)")
    aggression_factor: float = Field(ge=0, description="Aggression Factor")
    hands_played: Optional[int] = Field(default=0, ge=0, description="Количество рук")


class OpponentProfileUpdate(BaseModel):
    """Обновление профиля оппонента"""
    vpip: Optional[float] = Field(None, ge=0, le=100)
    pfr: Optional[float] = Field(None, ge=0, le=100)
    three_bet_pct: Optional[float] = Field(None, ge=0, le=100)
    aggression_factor: Optional[float] = Field(None, ge=0)
    hands_played: Optional[int] = Field(None, ge=0)
    classification: Optional[str] = None


class StatsResponse(BaseModel):
    """Общая статистика бота"""
    total_hands: int = Field(description="Всего раздач")
    total_decisions: int = Field(description="Всего решений")
    total_sessions: int = Field(default=0, description="Всего сессий")
    active_sessions: int = Field(default=0, description="Активных сессий")
    total_opponents: int = Field(description="Всего профилей оппонентов")
    active_checkpoints: int = Field(description="Активных чекпоинтов")
    total_profit: float = Field(default=0.0, description="Суммарный профит (в валюте логов)")
    total_rake: float = Field(default=0.0, description="Суммарный рейк (в валюте логов)")
    winrate_bb_100: float = Field(default=0.0, description="Оценка winrate bb/100 (упрощенно)")
    last_hand_time: Optional[datetime] = Field(None, description="Время последней раздачи")
    last_decision_time: Optional[datetime] = Field(None, description="Время последнего решения")


class CheckpointResponse(BaseModel):
    """Информация о чекпоинте"""
    id: int
    checkpoint_id: str
    version: str
    format: str
    training_iterations: int
    is_active: bool
    file_path: Optional[str]
    created_at: datetime


class HandHistoryResponse(BaseModel):
    """История раздачи"""
    id: int
    hand_id: str
    table_id: str
    limit_type: str
    result: Optional[float]
    pot_size: Optional[float]
    hero_cards: Optional[str]
    board_cards: Optional[str]
    created_at: datetime


class DecisionHistoryResponse(BaseModel):
    """История решения"""
    id: int
    hand_id: str
    table_id: Optional[str] = Field(default=None, description="ID стола (если доступно)")
    street: str
    action: str
    amount: Optional[float]
    pot_size: Optional[float]
    latency_ms: Optional[int]
    created_at: datetime


class HandLogBulkRequest(BaseModel):
    """Массовая загрузка раздач"""
    hands: List[HandLogRequest] = Field(description="Список раздач для загрузки")
    skip_existing: bool = Field(default=True, description="Пропускать существующие раздачи")


class OpponentProfileBulkRequest(BaseModel):
    """Массовая загрузка профилей оппонентов"""
    profiles: List[OpponentProfileCreate] = Field(description="Список профилей для загрузки")
    skip_existing: bool = Field(default=True, description="Пропускать существующие профили")
    update_existing: bool = Field(default=False, description="Обновлять существующие профили")


class SessionCreate(BaseModel):
    """Начало игровой сессии"""
    session_id: str = Field(description="ID сессии")
    limit_type: str = Field(description="Лимит (NL10, NL25, etc.)")
    table_ids: Optional[List[str]] = Field(default=None, description="ID столов")


class SessionEnd(BaseModel):
    """Завершение игровой сессии"""
    session_id: str = Field(description="ID сессии")
    hands_played: Optional[int] = Field(default=None, description="Сыграно раздач")
    total_profit: Optional[float] = Field(default=None, description="Общий профит")


class SessionResponse(BaseModel):
    """Информация о сессии"""
    session_id: str
    limit_type: str
    period_start: datetime
    period_end: Optional[datetime]
    hands_played: int
    vpip: float
    pfr: float
    three_bet_pct: float
    aggression_factor: float
    winrate_bb_100: float
    profit_bb_100: float  # Profit in bb/100
    total_rake: float
    rake_per_hour: float
    rake_100: float  # Rake per 100 hands
    hands_per_hour: float  # Hands per hour
    avg_pot_size: float


class TrainingStart(BaseModel):
    """Запуск обучения"""
    format: str = Field(description="Формат (NL10, NL25, etc.)")
    iterations: int = Field(ge=1000, le=1000000, description="Количество итераций")
    checkpoint_version: Optional[str] = Field(default=None, description="Версия чекпоинта")


class TrainingStatus(BaseModel):
    """Статус обучения"""
    is_running: bool
    current_iteration: Optional[int]
    total_iterations: Optional[int]
    format: Optional[str]
    start_time: Optional[datetime]
    estimated_completion: Optional[datetime]


class BulkOperationResponse(BaseModel):
    """Результат массовой операции"""
    status: str = Field(description="Статус операции")
    total_requested: int = Field(description="Всего запрошено")
    successful: Optional[int] = Field(default=None, description="Успешно обработано")
    created: Optional[int] = Field(default=None, description="Создано новых")
    updated: Optional[int] = Field(default=None, description="Обновлено")
    failed: int = Field(description="Провалено")
    errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Список ошибок")


class SessionStartResponse(BaseModel):
    """Ответ при старте сессии"""
    status: str
    session_id: str
    limit_type: str
    start_time: datetime


class SessionEndResponse(BaseModel):
    """Ответ при завершении сессии"""
    status: str
    session_id: str
    duration_minutes: float
    hands_played: int
    winrate_bb_100: float
    total_rake: float
    rake_per_hour: float


class SessionListItem(BaseModel):
    """Элемент списка сессий"""
    session_id: str
    limit_type: str
    period_start: datetime
    period_end: Optional[datetime]
    hands_played: int
    winrate_bb_100: float
    total_rake: float
    is_active: bool


class TrainingStartResponse(BaseModel):
    """Ответ при запуске обучения"""
    status: str
    format: str
    iterations: int
    message: str


class TrainingStopResponse(BaseModel):
    """Ответ при остановке обучения"""
    status: str
    message: str


class CheckpointActivateResponse(BaseModel):
    """Ответ при активации чекпоинта"""
    status: str
    checkpoint_id: str
    format: str
    training_iterations: int


class WinrateStatsResponse(BaseModel):
    """Статистика винрейта"""
    period_days: int
    total_hands: int
    total_profit: float
    winrate_bb_100: float
    avg_profit_per_hand: float


class HandLogResponse(BaseModel):
    """Ответ при логировании раздачи"""
    status: str
    hand_id: str


# ============================================
# Week 3: Agent Protocol Schemas
# ============================================

class AgentHeartbeatRequest(BaseModel):
    """Запрос heartbeat от агента"""
    agent_id: str
    session_id: Optional[str] = None
    status: Optional[str] = Field(default="online", description="Статус агента")
    version: Optional[str] = None
    errors: Optional[List[str]] = Field(default=None, description="Список последних ошибок")


class AgentHeartbeatResponse(BaseModel):
    """Ответ на heartbeat"""
    status: str
    agent_id: str
    commands: List[Dict] = Field(default=[], description="Команды для агента")


class AgentCommandRequest(BaseModel):
    """Запрос на отправку команды агенту"""
    command: str = Field(description="Команда: pause, resume, stop, sit_out")
    reason: Optional[str] = Field(default=None, description="Причина команды")


class AgentCommandResponse(BaseModel):
    """Ответ на отправку команды"""
    status: str
    agent_id: str
    command: str
    message: str


class AgentStatusResponse(BaseModel):
    """Статус агента"""
    agent_id: str
    status: str
    last_seen: Optional[datetime]
    version: Optional[str]
    assigned_session_id: Optional[int]
    heartbeat_lag_seconds: Optional[float] = Field(description="Секунд с последнего heartbeat")
    errors: List[str] = Field(default=[], description="Последние ошибки")


class AgentListResponse(BaseModel):
    """Информация об агенте в списке"""
    agent_id: str
    status: str
    last_seen: Optional[datetime]
    version: Optional[str]
    assigned_session_id: Optional[int]
    heartbeat_lag_seconds: Optional[float]
