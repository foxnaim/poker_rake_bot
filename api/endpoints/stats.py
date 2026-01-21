"""Endpoints для статистики и аналитики"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from api.schemas import (
    StatsResponse,
    CheckpointResponse,
    HandHistoryResponse,
    DecisionHistoryResponse,
    CheckpointActivateResponse,
    WinrateStatsResponse
)
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["stats"])


def _resolve_table_key(db: Session, table_id: Optional[str]) -> Optional[str]:
    """
    Приводит table_id к table_key (Table.external_table_id), если возможно.
    Иначе возвращает исходное значение.
    """
    if not table_id:
        return None

    table_id_str = str(table_id)

    try:
        from data.models import Table
        # 1) Если прилетел PK в виде числа -> ищем Table.id
        try:
            pk = int(table_id_str)
        except (TypeError, ValueError):
            pk = None

        table = None
        if pk is not None:
            table = db.query(Table).filter(Table.id == pk).first()
        # 2) Иначе/дополнительно пробуем как external_table_id
        if table is None:
            table = db.query(Table).filter(Table.external_table_id == table_id_str).first()

        return table.external_table_id if table and table.external_table_id else table_id_str
    except Exception:
        return table_id_str


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db)
):
    """
    Получает общую статистику бота

    Возвращает:
    - Общее количество раздач
    - Количество решений
    - Количество профилей оппонентов
    - Количество активных чекпоинтов
    - Uptime
    """
    from data.models import Hand, DecisionLog, OpponentProfile, BotStats, BotSession

    total_hands = db.query(func.count(Hand.id)).scalar() or 0
    total_decisions = db.query(func.count(DecisionLog.id)).scalar() or 0
    total_opponents = db.query(func.count(OpponentProfile.id)).scalar() or 0

    # Сессии:
    # - control-plane (bot_sessions) — основной контур
    total_control_sessions = db.query(func.count(BotSession.id)).scalar() or 0
    active_control_sessions = db.query(func.count(BotSession.id)).filter(
        BotSession.status.in_(["starting", "running", "paused"])
    ).scalar() or 0
    # - legacy (bot_stats) — оставляем для совместимости/диагностики
    total_legacy_sessions = db.query(func.count(BotStats.id)).scalar() or 0
    active_legacy_sessions = db.query(func.count(BotStats.id)).filter(BotStats.period_end.is_(None)).scalar() or 0

    # Для обратной совместимости поля total_sessions/active_sessions считаем по control-plane
    total_sessions = total_control_sessions
    active_sessions = active_control_sessions

    # Финансовые агрегаты (из hands)
    total_profit = db.query(func.sum(Hand.hero_result)).scalar()
    total_profit = float(total_profit) if total_profit is not None else 0.0

    total_rake = db.query(func.sum(Hand.rake_amount)).scalar()
    total_rake = float(total_rake) if total_rake is not None else 0.0

    # Упрощенный winrate (bb/100), считаем BB=1.0 как в текущем коде сессий
    winrate_bb_100 = 0.0
    if total_hands > 0:
        winrate_bb_100 = (total_profit / total_hands) * 100.0

    # Активные чекпоинты
    from data.models import TrainingCheckpoint
    active_checkpoints = db.query(func.count(TrainingCheckpoint.id)).filter(
        TrainingCheckpoint.is_active == True
    ).scalar() or 0

    # Последняя раздача
    last_hand = db.query(Hand).order_by(desc(Hand.created_at)).first()
    last_hand_time = last_hand.created_at if last_hand else None

    # Последнее решение
    last_decision = db.query(DecisionLog).order_by(desc(DecisionLog.timestamp)).first()
    last_decision_time = last_decision.timestamp if last_decision else None

    return StatsResponse(
        total_hands=total_hands,
        total_decisions=total_decisions,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_control_sessions=total_control_sessions,
        active_control_sessions=active_control_sessions,
        total_legacy_sessions=total_legacy_sessions,
        active_legacy_sessions=active_legacy_sessions,
        total_opponents=total_opponents,
        active_checkpoints=active_checkpoints,
        total_profit=total_profit,
        total_rake=total_rake,
        winrate_bb_100=winrate_bb_100,
        last_hand_time=last_hand_time,
        last_decision_time=last_decision_time
    )


@router.get("/checkpoints", response_model=List[CheckpointResponse])
async def get_checkpoints(
    format: Optional[str] = Query(None, description="Фильтр по формату (NL10, NL25, etc.)"),
    active_only: bool = Query(False, description="Только активные"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Получает список чекпоинтов обучения

    Параметры:
    - format: фильтр по формату (NL10, NL25, etc.)
    - active_only: только активные чекпоинты
    - limit: максимум записей
    """
    from data.models import TrainingCheckpoint

    query = db.query(TrainingCheckpoint)

    if format:
        query = query.filter(TrainingCheckpoint.format == format)

    if active_only:
        query = query.filter(TrainingCheckpoint.is_active == True)

    # Сортировка по дате (новые первые)
    query = query.order_by(desc(TrainingCheckpoint.created_at))

    checkpoints = query.limit(limit).all()

    return [
        CheckpointResponse(
            id=cp.id,
            checkpoint_id=cp.checkpoint_id,
            version=cp.version,
            format=cp.format,
            training_iterations=cp.training_iterations,
            is_active=cp.is_active,
            file_path=cp.file_path,
            created_at=cp.created_at
        )
        for cp in checkpoints
    ]


@router.post("/checkpoint/{checkpoint_id}/activate", response_model=CheckpointActivateResponse)
async def activate_checkpoint(
    checkpoint_id: str,
    db: Session = Depends(get_db)
):
    """
    Активирует чекпоинт (деактивирует все остальные того же формата)

    ВАЖНО: Это изменит текущую стратегию бота!
    """
    from data.models import TrainingCheckpoint

    # Находим чекпоинт
    checkpoint = db.query(TrainingCheckpoint).filter(
        TrainingCheckpoint.checkpoint_id == checkpoint_id
    ).first()

    if not checkpoint:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Чекпоинт {checkpoint_id} не найден"
        )

    # Деактивируем все чекпоинты того же формата
    db.query(TrainingCheckpoint).filter(
        TrainingCheckpoint.format == checkpoint.format
    ).update({"is_active": False})

    # Активируем выбранный
    checkpoint.is_active = True

    db.commit()
    db.refresh(checkpoint)

    return CheckpointActivateResponse(
        status="success",
        checkpoint_id=checkpoint.checkpoint_id,
        format=checkpoint.format,
        training_iterations=checkpoint.training_iterations
    )


@router.get("/hands/recent", response_model=List[HandHistoryResponse])
async def get_recent_hands(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, description="Смещение (пагинация)"),
    table_id: Optional[str] = Query(None, description="Фильтр по столу"),
    db: Session = Depends(get_db)
):
    """
    Получает последние раздачи

    Параметры:
    - limit: максимум записей
    - table_id: фильтр по ID стола
    """
    from data.models import Hand

    query = db.query(Hand)

    if table_id:
        # Поддерживаем фильтр как по PK (строкой), так и по table_key (external_table_id)
        candidates = {str(table_id)}
        try:
            from data.models import Table
            # a) если фильтр = число -> добавим external_table_id этого стола
            try:
                pk = int(str(table_id))
            except (TypeError, ValueError):
                pk = None
            if pk is not None:
                t = db.query(Table).filter(Table.id == pk).first()
                if t and t.external_table_id:
                    candidates.add(t.external_table_id)
            # b) если фильтр = external_table_id -> добавим str(id) чтобы матчить старые логи
            t2 = db.query(Table).filter(Table.external_table_id == str(table_id)).first()
            if t2:
                candidates.add(str(t2.id))
        except Exception:
            pass
        query = query.filter(Hand.table_id.in_(list(candidates)))

    query = query.order_by(desc(Hand.created_at))

    hands = query.offset(offset).limit(limit).all()

    return [
        HandHistoryResponse(
            id=h.id,
            hand_id=h.hand_id,
            table_id=h.table_id,
            table_key=_resolve_table_key(db, h.table_id),
            limit_type=h.limit_type,
            result=float(h.hero_result) if h.hero_result else None,
            pot_size=float(h.pot_size) if h.pot_size else None,
            hero_cards=h.hero_cards,
            board_cards=h.board_cards,
            created_at=h.created_at
        )
        for h in hands
    ]


@router.get("/decisions/history", response_model=List[DecisionHistoryResponse])
async def get_decision_history(
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None, description="Фильтр по действию (fold, call, raise, all_in)"),
    street: Optional[str] = Query(None, description="Фильтр по улице (preflop, flop, turn, river)"),
    db: Session = Depends(get_db)
):
    """
    Получает историю решений бота

    Параметры:
    - limit: максимум записей
    - action: фильтр по действию
    - street: фильтр по улице
    """
    from data.models import DecisionLog

    query = db.query(DecisionLog)

    if action:
        query = query.filter(DecisionLog.final_action == action)

    if street:
        query = query.filter(DecisionLog.street == street)

    query = query.order_by(desc(DecisionLog.timestamp))

    decisions = query.limit(limit).all()

    return [
        DecisionHistoryResponse(
            id=d.id,
            hand_id=d.hand_id,
            table_id=d.game_state.get("table_id") if isinstance(d.game_state, dict) else None,
            table_key=_resolve_table_key(
                db,
                (d.game_state.get("table_id") if isinstance(d.game_state, dict) else None),
            ),
            street=d.street,
            action=d.final_action,
            amount=float(d.action_amount) if d.action_amount else None,
            pot_size=float(d.game_state.get("pot")) if isinstance(d.game_state, dict) and d.game_state.get("pot") is not None else None,
            latency_ms=d.latency_ms,
            created_at=d.timestamp
        )
        for d in decisions
    ]


@router.get("/stats/winrate", response_model=WinrateStatsResponse)
async def get_winrate_stats(
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    db: Session = Depends(get_db)
):
    """
    Получает статистику винрейта

    Возвращает:
    - Общий винрейт (bb/100)
    - Количество раздач
    - Общий профит
    """
    from data.models import Hand

    # Период
    since = datetime.utcnow() - timedelta(days=days)

    # Запрос рук за период
    query = db.query(
        func.count(Hand.id).label('total_hands'),
        func.sum(Hand.hero_result).label('total_profit')
    ).filter(Hand.created_at >= since)

    result = query.first()

    total_hands = result.total_hands or 0
    total_profit = float(result.total_profit) if result.total_profit else 0.0

    # Вычисляем bb/100
    # Предполагаем NL10 (big blind = 1.0)
    big_blind = 1.0
    winrate_bb_100 = 0.0

    if total_hands > 0:
        winrate_bb_100 = (total_profit / total_hands) * 100 / big_blind

    return WinrateStatsResponse(
        period_days=days,
        total_hands=total_hands,
        total_profit=total_profit,
        winrate_bb_100=round(winrate_bb_100, 2),
        avg_profit_per_hand=round(total_profit / total_hands, 4) if total_hands > 0 else 0.0
    )
