"""
Сервис аудит-логирования операций оператора

Фиксирует все важные операции:
- CRUD операции над сущностями (bots, rooms, tables, configs, sessions)
- Управление сессиями (start, pause, stop)
- Изменения конфигураций и рейк-моделей
- Действия с API ключами
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager
import json

from data.models import AuditLog


class AuditAction:
    """Константы для типов действий"""
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


class AuditEntityType:
    """Константы для типов сущностей"""
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


class AuditService:
    """Сервис для записи аудит-логов"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Записывает событие в аудит-лог

        Args:
            action: Тип действия (create, update, delete, start_session, etc.)
            entity_type: Тип сущности (bot, room, table, etc.)
            entity_id: ID сущности (опционально)
            user_id: ID пользователя/API ключа (опционально)
            old_values: Старые значения (для update)
            new_values: Новые значения
            metadata: Дополнительные данные

        Returns:
            Созданная запись AuditLog
        """
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            meta_data=metadata
        )

        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)

        return audit_entry

    def log_create(
        self,
        entity_type: str,
        entity_id: int,
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Логирует создание сущности"""
        return self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            new_values=new_values,
            metadata=metadata
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: int,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Логирует обновление сущности"""
        return self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: int,
        old_values: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Логирует удаление сущности"""
        return self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=old_values,
            metadata=metadata
        )

    def log_session_start(
        self,
        session_id: int,
        bot_id: int,
        table_id: int,
        config: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Логирует запуск сессии бота"""
        return self.log(
            action=AuditAction.START_SESSION,
            entity_type=AuditEntityType.BOT_SESSION,
            entity_id=session_id,
            user_id=user_id,
            new_values={
                "bot_id": bot_id,
                "table_id": table_id,
                "config": config,
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        )

    def log_session_stop(
        self,
        session_id: int,
        reason: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Логирует остановку сессии бота"""
        return self.log(
            action=AuditAction.STOP_SESSION,
            entity_type=AuditEntityType.BOT_SESSION,
            entity_id=session_id,
            user_id=user_id,
            new_values={
                "reason": reason,
                "stopped_at": datetime.now(timezone.utc).isoformat(),
                "final_stats": stats
            }
        )

    def log_agent_command(
        self,
        agent_id: str,
        command: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Логирует команду агенту"""
        return self.log(
            action=AuditAction.AGENT_COMMAND,
            entity_type=AuditEntityType.AGENT,
            user_id=user_id,
            new_values={
                "agent_id": agent_id,
                "command": command,
                "reason": reason,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
        )


def get_audit_service(db: Session) -> AuditService:
    """Фабрика для получения AuditService"""
    return AuditService(db)


@contextmanager
def audit_context(db: Session, user_id: Optional[str] = None):
    """
    Контекстный менеджер для аудит-логирования

    Usage:
        with audit_context(db, user_id="admin") as audit:
            audit.log_create("bot", bot.id, {"alias": "bot1"})
    """
    service = AuditService(db)
    try:
        yield service
    except Exception as e:
        # Логируем ошибку как системное событие
        try:
            service.log(
                action="error",
                entity_type=AuditEntityType.SYSTEM,
                user_id=user_id,
                metadata={"error": str(e), "type": type(e).__name__}
            )
        except:
            pass  # Не фейлим основную операцию если аудит не сработал
        raise
