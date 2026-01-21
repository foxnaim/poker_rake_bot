"""Endpoints для управления API ключами"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import secrets
import hashlib

from data.database import get_db
from data.models_v1_2 import APIKey
from api.auth import require_admin, require_api_key

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class APIKeyCreate(BaseModel):
    """Создание API ключа"""
    client_name: str
    permissions: List[str] = ["decide_only", "log_only"]
    rate_limit_per_minute: int = 120
    is_admin: bool = False  # Week 2: admin flag
    expires_at: Optional[str] = None


class APIKeyResponse(BaseModel):
    """Ответ с API ключом"""
    key_id: int
    api_key: str
    api_secret: str
    client_name: str
    permissions: List[str]
    is_admin: bool = False
    rate_limit_per_minute: int
    is_active: bool
    created_at: str


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)  # Только админы
):
    """
    Создает новый API ключ
    
    Требует: admin права
    """
    # Генерируем ключи
    api_key = f"pk_live_{secrets.token_urlsafe(32)}"
    api_secret = secrets.token_urlsafe(64)
    
    # Создаем запись
    db_key = APIKey(
        api_key=api_key,
        api_secret=api_secret,
        client_name=request.client_name,
        permissions=request.permissions,
        is_admin=request.is_admin,
        rate_limit_per_minute=request.rate_limit_per_minute,
        is_active=True
    )
    
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    return APIKeyResponse(
        key_id=db_key.key_id,
        api_key=db_key.api_key,
        api_secret=db_key.api_secret,
        client_name=db_key.client_name,
        permissions=db_key.permissions,
        rate_limit_per_minute=db_key.rate_limit_per_minute,
        is_active=db_key.is_active,
        created_at=db_key.created_at.isoformat()
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_api_key)
):
    """Список всех API ключей (только для админов)"""
    keys = db.query(APIKey).all()
    
    return [
        APIKeyResponse(
            key_id=k.key_id,
            api_key=k.api_key,
            api_secret="***hidden***",  # Не показываем секрет
        client_name=k.client_name,
        permissions=k.permissions,
        is_admin=getattr(k, 'is_admin', False),
        rate_limit_per_minute=k.rate_limit_per_minute,
        is_active=k.is_active,
        created_at=k.created_at.isoformat()
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_api_key)
):
    """Удаляет API ключ"""
    key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    
    return {"status": "deleted", "key_id": key_id}


@router.patch("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_api_key)
):
    """Активирует/деактивирует API ключ"""
    key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.is_active = not key.is_active
    db.commit()
    
    return {"key_id": key_id, "is_active": key.is_active}
