"""Admin endpoints для просмотра аудит-лога"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from data.database import get_db
from data.models import AuditLog
from api.auth import require_admin
from api.audit import get_audit_logs, get_entity_history

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "audit"])


class AuditLogResponse(BaseModel):
    """Ответ с записью аудит-лога"""
    id: int
    user_id: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[int]
    old_values: Optional[dict]
    new_values: Optional[dict]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditSummaryResponse(BaseModel):
    """Сводка по аудит-логу"""
    total_entries: int
    by_entity_type: dict
    by_action: dict
    recent_activity: List[AuditLogResponse]


@router.get("/audit", response_model=List[AuditLogResponse])
async def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    entity_id: Optional[int] = Query(None, description="Фильтр по ID сущности"),
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    user_id: Optional[str] = Query(None, description="Фильтр по пользователю"),
    limit: int = Query(100, le=500, description="Лимит записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """
    Получает записи аудит-лога с фильтрацией

    Примеры:
    - /audit?entity_type=bot_session&action=start_session
    - /audit?user_id=admin_key_123
    - /audit?limit=50&offset=0
    """
    logs = get_audit_logs(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        limit=limit,
        offset=offset
    )

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values,
            new_values=log.new_values,
            metadata=log.meta_data,
            created_at=log.created_at
        )
        for log in logs
    ]


@router.get("/audit/entity/{entity_type}/{entity_id}", response_model=List[AuditLogResponse])
async def get_entity_audit_history(
    entity_type: str,
    entity_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """
    Получает историю изменений конкретной сущности

    Примеры:
    - /audit/entity/bot/1 - история бота #1
    - /audit/entity/room/5 - история комнаты #5
    """
    logs = get_entity_history(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values,
            new_values=log.new_values,
            metadata=log.meta_data,
            created_at=log.created_at
        )
        for log in logs
    ]


@router.get("/audit/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """
    Получает сводку по аудит-логу

    Возвращает:
    - Общее число записей
    - Разбивка по типам сущностей
    - Разбивка по действиям
    - Последние 10 записей
    """
    from sqlalchemy import func

    # Общее число записей
    total = db.query(func.count(AuditLog.id)).scalar()

    # Группировка по entity_type
    by_entity = db.query(
        AuditLog.entity_type,
        func.count(AuditLog.id)
    ).group_by(AuditLog.entity_type).all()

    # Группировка по action
    by_action = db.query(
        AuditLog.action,
        func.count(AuditLog.id)
    ).group_by(AuditLog.action).all()

    # Последние 10 записей
    recent = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).limit(10).all()

    return AuditSummaryResponse(
        total_entries=total or 0,
        by_entity_type={row[0]: row[1] for row in by_entity},
        by_action={row[0]: row[1] for row in by_action},
        recent_activity=[
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                old_values=log.old_values,
                new_values=log.new_values,
                metadata=log.meta_data,
                created_at=log.created_at
            )
            for log in recent
        ]
    )
