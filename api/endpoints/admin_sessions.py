"""Admin endpoints для управления сессиями ботов"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from data.database import get_db
from data.models import BotSession, Bot, Table, BotConfig
from api.auth import require_admin
from api.audit import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "sessions"])


class SessionStartRequest(BaseModel):
    """Запрос на старт сессии"""
    bot_id: int
    # Можно указать либо table_id (PK), либо table_key (строковый ключ для агента)
    table_id: Optional[int] = None
    table_key: Optional[str] = None
    limit: str
    style: Optional[str] = None  # Если не указан, используется default_style бота
    bot_config_id: Optional[int] = None  # Если не указан, используется default config


class SessionStartResponse(BaseModel):
    """Ответ при старте сессии"""
    session_id: str
    bot_id: int
    table_id: int
    table_key: Optional[str] = None
    bot_config_id: Optional[int]
    status: str
    started_at: datetime
    applied_config: Optional[dict] = None


class SessionResponse(BaseModel):
    """Ответ с сессией"""
    id: int
    session_id: str
    bot_id: int
    table_id: int
    table_key: Optional[str] = None
    bot_config_id: Optional[int]
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    hands_played: int
    profit: float
    rake_paid: float
    bb_100: float
    rake_100: float
    last_error: Optional[str]
    meta: Optional[dict]

    class Config:
        from_attributes = True


@router.post("/session/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Запускает новую сессию бота"""
    # Проверяем бота
    bot = db.query(Bot).filter(Bot.id == request.bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    if not bot.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot is not active"
        )
    
    # Проверяем стол (по id или по table_key)
    if request.table_id is None and not request.table_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either table_id or table_key"
        )

    table = None
    if request.table_id is not None:
        table = db.query(Table).filter(Table.id == request.table_id).first()
    if table is None and request.table_key:
        table = db.query(Table).filter(Table.external_table_id == request.table_key).first()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Проверяем, что нет активной сессии для этого бота
    active_session = db.query(BotSession).filter(
        BotSession.bot_id == request.bot_id,
        BotSession.status.in_(["starting", "running", "paused"])
    ).first()
    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot already has an active session: {active_session.session_id}"
        )
    
    # Определяем конфиг
    bot_config_id = request.bot_config_id
    applied_config = None
    
    if bot_config_id:
        config = db.query(BotConfig).filter(BotConfig.id == bot_config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot config not found"
            )
        applied_config = {
            "target_vpip": float(config.target_vpip),
            "target_pfr": float(config.target_pfr),
            "target_af": float(config.target_af),
            "exploit_weights": config.exploit_weights,
            "max_winrate_cap": float(config.max_winrate_cap) if config.max_winrate_cap else None
        }
    else:
        # Используем default config бота
        default_config = db.query(BotConfig).filter(
            BotConfig.bot_id == request.bot_id,
            BotConfig.is_default == True
        ).first()
        if default_config:
            bot_config_id = default_config.id
            applied_config = {
                "target_vpip": float(default_config.target_vpip),
                "target_pfr": float(default_config.target_pfr),
                "target_af": float(default_config.target_af),
                "exploit_weights": default_config.exploit_weights,
                "max_winrate_cap": float(default_config.max_winrate_cap) if default_config.max_winrate_cap else None
            }
    
    # Создаем сессию
    session_id = f"session_{uuid.uuid4().hex[:16]}"
    session = BotSession(
        session_id=session_id,
        bot_id=request.bot_id,
        table_id=table.id,
        bot_config_id=bot_config_id,
        status="starting",
        meta={"style": request.style or bot.default_style, "limit": request.limit}
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)

    # Совместимость со старым контуром статистики (bot_stats),
    # чтобы /api/v1/stats и /api/v1/sessions/* работали согласованно.
    from data.models import BotStats
    existing_stats = db.query(BotStats).filter(
        BotStats.session_id == session_id,
        BotStats.period_end.is_(None),
    ).first()
    if not existing_stats:
        stats_row = BotStats(
            session_id=session_id,
            limit_type=request.limit,
            period_start=session.started_at,
            period_end=None,
        )
        db.add(stats_row)
        db.commit()
    
    audit_log_create(db, admin_key, "start_session", "bot_session", session.id, None, {"session_id": session_id})
    
    return SessionStartResponse(
        session_id=session_id,
        bot_id=request.bot_id,
        table_id=table.id,
        table_key=table.external_table_id,
        bot_config_id=bot_config_id,
        status=session.status,
        started_at=session.started_at,
        applied_config=applied_config
    )


@router.post("/session/{session_id}/pause", response_model=SessionResponse)
async def pause_session(
    session_id: str,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Приостанавливает сессию"""
    session = db.query(BotSession).filter(BotSession.session_id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.status not in ["running", "starting"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not running (current status: {session.status})"
        )
    
    old_status = session.status
    session.status = "paused"
    db.commit()
    db.refresh(session)
    
    audit_log_create(db, admin_key, "pause_session", "bot_session", session.id, {"status": old_status}, {"status": "paused"})
    
    return session


@router.post("/session/{session_id}/stop", response_model=SessionResponse)
async def stop_session(
    session_id: str,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Останавливает сессию"""
    session = db.query(BotSession).filter(BotSession.session_id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.status == "stopped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already stopped"
        )
    
    old_status = session.status
    session.status = "stopped"
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    # Закрываем соответствующую запись bot_stats (если есть)
    from data.models import BotStats
    stats_row = db.query(BotStats).filter(
        BotStats.session_id == session_id,
        BotStats.period_end.is_(None),
    ).first()
    if stats_row:
        stats_row.period_end = session.ended_at
        db.commit()
    
    audit_log_create(db, admin_key, "stop_session", "bot_session", session.id, {"status": old_status}, {"status": "stopped"})
    
    return session


@router.get("/sessions/recent", response_model=List[SessionResponse])
async def get_recent_sessions(
    limit: int = 50,
    status_filter: Optional[str] = None,
    bot_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает последние сессии"""
    query = db.query(BotSession)
    
    if status_filter:
        query = query.filter(BotSession.status == status_filter)
    if bot_id:
        query = query.filter(BotSession.bot_id == bot_id)
    
    sessions = query.order_by(BotSession.started_at.desc()).limit(limit).all()
    return sessions


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает сессию по ID"""
    session = db.query(BotSession).filter(BotSession.session_id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session
