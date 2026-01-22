"""Admin endpoints для управления ботами"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from data.database import get_db
from data.models import Bot
from api.auth import require_admin
from api.audit import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "bots"])


class BotCreate(BaseModel):
    """Создание бота"""
    alias: str = Field(..., min_length=1, max_length=100, description="Алиас бота (уникальный)")
    default_style: str = Field(default="balanced", pattern="^(balanced|aggressive|tight|loose)$", description="Стиль игры по умолчанию")
    default_limit: str = Field(default="NL10", pattern="^NL\\d+$", description="Лимит по умолчанию (NL10, NL50, etc.)")
    active: bool = Field(default=True, description="Активен ли бот")


class BotUpdate(BaseModel):
    """Обновление бота"""
    alias: Optional[str] = None
    default_style: Optional[str] = None
    default_limit: Optional[str] = None
    active: Optional[bool] = None


class BotResponse(BaseModel):
    """Ответ с ботом"""
    id: int
    alias: str
    default_style: str
    default_limit: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/bots", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    request: BotCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Создает нового бота"""
    # Проверяем уникальность alias
    existing = db.query(Bot).filter(Bot.alias == request.alias).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot with alias '{request.alias}' already exists"
        )
    
    bot = Bot(
        alias=request.alias,
        default_style=request.default_style,
        default_limit=request.default_limit,
        active=request.active
    )
    
    db.add(bot)
    db.commit()
    db.refresh(bot)
    
    # Audit log
    audit_log_create(db, admin_key, "create", "bot", bot.id, None, {"alias": bot.alias})
    
    return bot


@router.get("/bots", response_model=List[BotResponse])
async def list_bots(
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Список всех ботов"""
    query = db.query(Bot)
    
    if active is not None:
        query = query.filter(Bot.active == active)
    
    bots = query.order_by(Bot.created_at.desc()).all()
    return bots


@router.get("/bots/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает бота по ID"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    return bot


@router.patch("/bots/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    request: BotUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Обновляет бота"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    old_values = {
        "alias": bot.alias,
        "default_style": bot.default_style,
        "default_limit": bot.default_limit,
        "active": bot.active
    }
    
    if request.alias is not None:
        # Проверяем уникальность
        existing = db.query(Bot).filter(Bot.alias == request.alias, Bot.id != bot_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bot with alias '{request.alias}' already exists"
            )
        bot.alias = request.alias
    
    if request.default_style is not None:
        bot.default_style = request.default_style
    if request.default_limit is not None:
        bot.default_limit = request.default_limit
    if request.active is not None:
        bot.active = request.active
    
    db.commit()
    db.refresh(bot)
    
    # Audit log
    new_values = {
        "alias": bot.alias,
        "default_style": bot.default_style,
        "default_limit": bot.default_limit,
        "active": bot.active
    }
    audit_log_create(db, admin_key, "update", "bot", bot.id, old_values, new_values)
    
    return bot


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Удаляет бота"""
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Audit log
    audit_log_create(db, admin_key, "delete", "bot", bot.id, {"alias": bot.alias}, None)
    
    db.delete(bot)
    db.commit()
    
    return None
