"""Аудит-лог (helper)

Интеграция с AuditService для записи событий аудита.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from data.models import AuditLog


# ============================================
# Константы для типов действий
# ============================================

class AuditAction:
    """Типы действий для аудита"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    START_SESSION = "start_session"
    PAUSE_SESSION = "pause_session"
    STOP_SESSION = "stop_session"
    ASSIGN_BOT = "assign_bot"
    ONBOARD_ROOM = "onboard_room"
    CHANGE_CONFIG = "change_config"
    CHANGE_RAKE_MODEL = "change_rake_model"
    AGENT_COMMAND = "agent_command"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    LOGIN = "login"
    LOGOUT = "logout"
    ERROR = "error"


class AuditEntityType:
    """Типы сущностей для аудита"""
    BOT = "bot"
    ROOM = "room"
    TABLE = "table"
    BOT_CONFIG = "bot_config"
    RAKE_MODEL = "rake_model"
    BOT_SESSION = "bot_session"
    AGENT = "agent"
    API_KEY = "api_key"
    USER = "user"
    SYSTEM = "system"


# ============================================
# Основные функции
# ============================================

def audit_log_create(
    db: Session,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """
    Создает запись в audit_log.

    Args:
        db: Сессия БД
        user_id: ID пользователя/API ключа
        action: Тип действия
        entity_type: Тип сущности
        entity_id: ID сущности
        old_values: Старые значения (для update)
        new_values: Новые значения
        metadata: Дополнительные данные

    Returns:
        Созданная запись AuditLog или None при ошибке
    """
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            meta_data=metadata,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit
    except Exception as e:
        # Не фейлим основную операцию если аудит не сработал
        try:
            db.rollback()
        except:
            pass
        return None


def audit_log_session_start(
    db: Session,
    user_id: str,
    session_id: int,
    bot_id: int,
    table_id: int,
    config: Dict[str, Any]
) -> Optional[AuditLog]:
    """Логирует запуск сессии бота"""
    return audit_log_create(
        db=db,
        user_id=user_id,
        action=AuditAction.START_SESSION,
        entity_type=AuditEntityType.BOT_SESSION,
        entity_id=session_id,
        new_values={
            "bot_id": bot_id,
            "table_id": table_id,
            "config": config,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
    )


def audit_log_session_stop(
    db: Session,
    user_id: str,
    session_id: int,
    reason: Optional[str] = None,
    stats: Optional[Dict[str, Any]] = None
) -> Optional[AuditLog]:
    """Логирует остановку сессии бота"""
    return audit_log_create(
        db=db,
        user_id=user_id,
        action=AuditAction.STOP_SESSION,
        entity_type=AuditEntityType.BOT_SESSION,
        entity_id=session_id,
        new_values={
            "reason": reason,
            "stopped_at": datetime.now(timezone.utc).isoformat(),
            "final_stats": stats
        }
    )


def audit_log_agent_command(
    db: Session,
    user_id: str,
    agent_id: str,
    command: str,
    reason: Optional[str] = None
) -> Optional[AuditLog]:
    """Логирует команду агенту"""
    return audit_log_create(
        db=db,
        user_id=user_id,
        action=AuditAction.AGENT_COMMAND,
        entity_type=AuditEntityType.AGENT,
        entity_id=None,
        new_values={
            "agent_id": agent_id,
            "command": command,
            "reason": reason,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
    )


def audit_log_error(
    db: Session,
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> Optional[AuditLog]:
    """Логирует системную ошибку"""
    return audit_log_create(
        db=db,
        user_id=user_id or "system",
        action=AuditAction.ERROR,
        entity_type=AuditEntityType.SYSTEM,
        entity_id=None,
        metadata={
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# ============================================
# Запросы к аудит-логу
# ============================================

def get_audit_logs(
    db: Session,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """
    Получает записи аудит-лога с фильтрацией

    Args:
        db: Сессия БД
        entity_type: Фильтр по типу сущности
        entity_id: Фильтр по ID сущности
        action: Фильтр по действию
        user_id: Фильтр по пользователю
        limit: Лимит записей
        offset: Смещение

    Returns:
        Список записей AuditLog
    """
    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()


def get_entity_history(
    db: Session,
    entity_type: str,
    entity_id: int,
    limit: int = 50
) -> List[AuditLog]:
    """
    Получает историю изменений сущности

    Args:
        db: Сессия БД
        entity_type: Тип сущности
        entity_id: ID сущности
        limit: Лимит записей

    Returns:
        Список записей AuditLog для данной сущности
    """
    return get_audit_logs(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )
