"""Endpoints для управления игровыми сессиями"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timezone

from api.schemas import SessionCreate, SessionEnd, SessionResponse, SessionStartResponse, SessionEndResponse, SessionListItem
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["sessions"])


def parse_big_blind(limit_type: str) -> float:
    """
    Парсит big blind из limit_type строки.

    Примеры:
        NL10 -> 0.10
        NL25 -> 0.25
        NL50 -> 0.50
        NL100 -> 1.00
        NL200 -> 2.00
        NL500 -> 5.00

    Args:
        limit_type: Строка лимита (NL10, NL25, etc.)

    Returns:
        Размер big blind в долларах
    """
    if not limit_type:
        return 1.0  # Default

    # Извлекаем числовую часть
    import re
    match = re.search(r'(\d+)', limit_type)
    if match:
        limit_value = int(match.group(1))
        # NL10 = $0.05/$0.10, NL25 = $0.10/$0.25, etc.
        return limit_value / 100.0

    return 1.0  # Default fallback


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionCreate,
    db: Session = Depends(get_db)
):
    """
    Начинает новую игровую сессию

    Создает запись в bot_stats для отслеживания сессии
    """
    from data.models import BotStats

    # Проверяем, нет ли уже активной сессии с таким ID
    existing = db.query(BotStats).filter(
        BotStats.session_id == request.session_id,
        BotStats.period_end == None
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Сессия {request.session_id} уже активна"
        )

    # Создаем новую сессию
    session = BotStats(
        session_id=request.session_id,
        limit_type=request.limit_type,
        period_start=datetime.utcnow(),
        period_end=None,  # Будет заполнено при завершении
        hands_played=0,
        vpip=0,
        pfr=0,
        three_bet_pct=0,
        aggression_factor=0,
        winrate_bb_100=0,
        total_rake=0,
        rake_per_hour=0,
        avg_pot_size=0
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "status": "started",
        "session_id": session.session_id,
        "limit_type": session.limit_type,
        "start_time": session.period_start
    }


@router.post("/session/end", response_model=SessionEndResponse)
async def end_session(
    request: SessionEnd,
    db: Session = Depends(get_db)
):
    """
    Завершает активную игровую сессию

    Вычисляет итоговую статистику на основе раздач
    """
    from data.models import BotStats, Hand

    # Находим активную сессию
    session = db.query(BotStats).filter(
        BotStats.session_id == request.session_id,
        BotStats.period_end == None
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Активная сессия {request.session_id} не найдена"
        )

    # Завершаем сессию
    session.period_end = datetime.utcnow()

    # Вычисляем статистику из рук за период сессии
    hands = db.query(Hand).filter(
        Hand.created_at >= session.period_start,
        Hand.created_at <= session.period_end,
        Hand.limit_type == session.limit_type
    ).all()

    if hands:
        session.hands_played = len(hands)
        total_profit = sum(float(h.hero_result) for h in hands)
        total_rake = sum(float(h.rake_amount) for h in hands)
        total_pot = sum(float(h.pot_size) for h in hands)

        # Вычисляем bb/100
        big_blind = parse_big_blind(session.limit_type)
        if session.hands_played > 0:
            session.winrate_bb_100 = (total_profit / session.hands_played) * 100 / big_blind
            session.profit_bb_100 = (total_profit / session.hands_played) * 100 / big_blind

        session.total_rake = total_rake

        # Rake per hour и hands per hour
        duration_hours = (session.period_end - session.period_start).total_seconds() / 3600
        if duration_hours > 0:
            session.rake_per_hour = total_rake / duration_hours
            session.hands_per_hour = session.hands_played / duration_hours
        
        # Rake per 100 hands
        if session.hands_played > 0:
            session.rake_100 = (total_rake / session.hands_played) * 100

        # Средний размер пота
        session.avg_pot_size = total_pot / session.hands_played if session.hands_played > 0 else 0
        
        # Обновляем Prometheus метрики
        from api.metrics import (
            bot_rake_100, bot_profit_bb_100, bot_hands_per_hour,
            session_hands_total, session_profit_total, session_rake_total
        )
        bot_rake_100.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.rake_100))
        bot_profit_bb_100.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.profit_bb_100))
        bot_hands_per_hour.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.hands_per_hour))
        session_hands_total.labels(session_id=session.session_id, limit_type=session.limit_type).inc(len(hands))
        session_profit_total.labels(session_id=session.session_id, limit_type=session.limit_type).set(total_profit)
        session_rake_total.labels(session_id=session.session_id, limit_type=session.limit_type).set(total_rake)

    # Или используем переданные данные
    if request.hands_played is not None:
        session.hands_played = request.hands_played
    if request.total_profit is not None:
        if session.hands_played > 0:
            big_blind = parse_big_blind(session.limit_type)
            session.winrate_bb_100 = (request.total_profit / session.hands_played) * 100 / big_blind

    db.commit()
    db.refresh(session)
    
    # Обновляем метрики - сессия завершена
    from api.metrics import session_active
    session_active.labels(limit_type=session.limit_type).dec()

    return {
        "status": "ended",
        "session_id": session.session_id,
        "duration_minutes": (session.period_end - session.period_start).total_seconds() / 60,
        "hands_played": session.hands_played,
        "winrate_bb_100": float(session.winrate_bb_100),
        "total_rake": float(session.total_rake),
        "rake_per_hour": float(session.rake_per_hour)
    }


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Получает информацию о сессии

    Работает как для активных, так и для завершенных сессий.
    Для активных сессий вычисляет статистику в реальном времени.
    """
    from data.models import BotStats, Hand

    session = db.query(BotStats).filter(
        BotStats.session_id == session_id
    ).order_by(desc(BotStats.period_start)).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Сессия {session_id} не найдена"
        )

    # Если сессия активна, обновляем статистику в реальном времени
    if session.period_end is None:
        period_end = datetime.utcnow()
        hands = db.query(Hand).filter(
            Hand.created_at >= session.period_start,
            Hand.created_at <= period_end,
            Hand.limit_type == session.limit_type
        ).all()
        
        if hands:
            session.hands_played = len(hands)
            total_profit = sum(float(h.hero_result) for h in hands)
            total_rake = sum(float(h.rake_amount) for h in hands)
            total_pot = sum(float(h.pot_size) for h in hands)
            
            big_blind = parse_big_blind(session.limit_type)
            if session.hands_played > 0:
                session.winrate_bb_100 = (total_profit / session.hands_played) * 100 / big_blind
                session.profit_bb_100 = (total_profit / session.hands_played) * 100 / big_blind
                session.rake_100 = (total_rake / session.hands_played) * 100
            
            session.total_rake = total_rake
            
            duration_hours = (period_end - session.period_start).total_seconds() / 3600
            if duration_hours > 0:
                session.rake_per_hour = total_rake / duration_hours
                session.hands_per_hour = session.hands_played / duration_hours
            
            session.avg_pot_size = total_pot / session.hands_played if session.hands_played > 0 else 0
            
            # Обновляем Prometheus метрики для активной сессии
            from api.metrics import (
                bot_rake_100, bot_profit_bb_100, bot_hands_per_hour,
                session_active, session_hands_total, session_profit_total, session_rake_total
            )
            bot_rake_100.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.rake_100))
            bot_profit_bb_100.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.profit_bb_100))
            bot_hands_per_hour.labels(limit_type=session.limit_type, session_id=session.session_id).set(float(session.hands_per_hour))
            session_active.labels(limit_type=session.limit_type).set(1.0)
            session_hands_total.labels(session_id=session.session_id, limit_type=session.limit_type).inc(len(hands))
            session_profit_total.labels(session_id=session.session_id, limit_type=session.limit_type).set(total_profit)
            session_rake_total.labels(session_id=session.session_id, limit_type=session.limit_type).set(total_rake)

    return SessionResponse(
        session_id=session.session_id,
        limit_type=session.limit_type,
        period_start=session.period_start,
        period_end=session.period_end,
        hands_played=session.hands_played,
        vpip=float(session.vpip),
        pfr=float(session.pfr),
        three_bet_pct=float(session.three_bet_pct),
        aggression_factor=float(session.aggression_factor),
        winrate_bb_100=float(session.winrate_bb_100),
        profit_bb_100=float(session.profit_bb_100 or session.winrate_bb_100),
        total_rake=float(session.total_rake),
        rake_per_hour=float(session.rake_per_hour),
        rake_100=float(session.rake_100 or 0),
        hands_per_hour=float(session.hands_per_hour or 0),
        avg_pot_size=float(session.avg_pot_size)
    )


@router.get("/sessions/recent", response_model=List[SessionListItem])
async def get_recent_sessions(
    limit: int = Query(50, ge=1, le=500),
    limit_type: Optional[str] = Query(None, description="Фильтр по лимиту"),
    db: Session = Depends(get_db)
):
    """
    Получает список последних сессий

    Параметры:
    - limit: максимум записей
    - limit_type: фильтр по лимиту (NL10, NL25, etc.)
    """
    from data.models import BotStats

    query = db.query(BotStats)

    if limit_type:
        query = query.filter(BotStats.limit_type == limit_type)

    query = query.order_by(desc(BotStats.period_start))

    sessions = query.limit(limit).all()

    return [
        SessionListItem(
            session_id=s.session_id,
            limit_type=s.limit_type,
            period_start=s.period_start,
            period_end=s.period_end,
            hands_played=s.hands_played,
            winrate_bb_100=float(s.winrate_bb_100),
            total_rake=float(s.total_rake),
            is_active=s.period_end is None
        )
        for s in sessions
    ]
