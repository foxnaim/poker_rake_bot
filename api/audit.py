"""Аудит-лог (helper)"""

from typing import Optional, Dict, Any

from sqlalchemy.orm import Session


def audit_log_create(
    db: Session,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Создает запись в audit_log."""
    from data.models import AuditLog

    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        # В ORM поле называется meta_data, но в БД колонка = "metadata"
        meta_data=metadata,
    )
    db.add(audit)
    db.commit()

