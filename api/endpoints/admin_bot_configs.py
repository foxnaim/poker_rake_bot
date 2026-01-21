"""Admin endpoints для управления конфигурациями ботов"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

from data.database import get_db
from data.models import BotConfig, Bot
from api.auth import require_admin
from api.schemas import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "bot-configs"])


class BotConfigCreate(BaseModel):
    """Создание конфигурации бота"""
    bot_id: int
    name: str
    target_vpip: float = 20.0
    target_pfr: float = 15.0
    target_af: float = 2.0
    exploit_weights: Dict[str, float] = {"preflop": 0.3, "flop": 0.4, "turn": 0.5, "river": 0.6}
    max_winrate_cap: Optional[float] = None
    anti_pattern_params: Optional[Dict] = None
    limit_types: Optional[List[str]] = None
    is_default: bool = False


class BotConfigUpdate(BaseModel):
    """Обновление конфигурации бота"""
    name: Optional[str] = None
    target_vpip: Optional[float] = None
    target_pfr: Optional[float] = None
    target_af: Optional[float] = None
    exploit_weights: Optional[Dict[str, float]] = None
    max_winrate_cap: Optional[float] = None
    anti_pattern_params: Optional[Dict] = None
    limit_types: Optional[List[str]] = None
    is_default: Optional[bool] = None


class BotConfigResponse(BaseModel):
    """Ответ с конфигурацией бота"""
    id: int
    bot_id: int
    name: str
    target_vpip: float
    target_pfr: float
    target_af: float
    exploit_weights: Dict
    max_winrate_cap: Optional[float]
    anti_pattern_params: Optional[Dict]
    limit_types: Optional[List[str]]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/bot-configs", response_model=BotConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_bot_config(
    request: BotConfigCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Создает новую конфигурацию бота"""
    # Проверяем бота
    bot = db.query(Bot).filter(Bot.id == request.bot_id).first()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Если это default config, снимаем default с других
    if request.is_default:
        db.query(BotConfig).filter(
            BotConfig.bot_id == request.bot_id,
            BotConfig.is_default == True
        ).update({"is_default": False})
    
    config = BotConfig(
        bot_id=request.bot_id,
        name=request.name,
        target_vpip=request.target_vpip,
        target_pfr=request.target_pfr,
        target_af=request.target_af,
        exploit_weights=request.exploit_weights,
        max_winrate_cap=request.max_winrate_cap,
        anti_pattern_params=request.anti_pattern_params,
        limit_types=request.limit_types,
        is_default=request.is_default
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    audit_log_create(db, admin_key, "create", "bot_config", config.id, None, {"bot_id": config.bot_id, "name": config.name})
    
    return config


@router.get("/bot-configs", response_model=List[BotConfigResponse])
async def list_bot_configs(
    bot_id: Optional[int] = None,
    is_default: Optional[bool] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Список всех конфигураций ботов"""
    query = db.query(BotConfig)
    
    if bot_id:
        query = query.filter(BotConfig.bot_id == bot_id)
    if is_default is not None:
        query = query.filter(BotConfig.is_default == is_default)
    
    configs = query.order_by(BotConfig.created_at.desc()).all()
    return configs


@router.get("/bot-configs/{config_id}", response_model=BotConfigResponse)
async def get_bot_config(
    config_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает конфигурацию бота по ID"""
    config = db.query(BotConfig).filter(BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot config not found"
        )
    return config


@router.patch("/bot-configs/{config_id}", response_model=BotConfigResponse)
async def update_bot_config(
    config_id: int,
    request: BotConfigUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Обновляет конфигурацию бота"""
    config = db.query(BotConfig).filter(BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot config not found"
        )
    
    old_values = {
        "target_vpip": float(config.target_vpip),
        "target_pfr": float(config.target_pfr),
        "target_af": float(config.target_af),
        "exploit_weights": config.exploit_weights,
        "max_winrate_cap": float(config.max_winrate_cap) if config.max_winrate_cap else None
    }
    
    if request.name is not None:
        config.name = request.name
    if request.target_vpip is not None:
        config.target_vpip = request.target_vpip
    if request.target_pfr is not None:
        config.target_pfr = request.target_pfr
    if request.target_af is not None:
        config.target_af = request.target_af
    if request.exploit_weights is not None:
        config.exploit_weights = request.exploit_weights
    if request.max_winrate_cap is not None:
        config.max_winrate_cap = request.max_winrate_cap
    if request.anti_pattern_params is not None:
        config.anti_pattern_params = request.anti_pattern_params
    if request.limit_types is not None:
        config.limit_types = request.limit_types
    if request.is_default is not None:
        # Если делаем default, снимаем default с других
        if request.is_default:
            db.query(BotConfig).filter(
                BotConfig.bot_id == config.bot_id,
                BotConfig.is_default == True,
                BotConfig.id != config_id
            ).update({"is_default": False})
        config.is_default = request.is_default
    
    db.commit()
    db.refresh(config)
    
    new_values = {
        "target_vpip": float(config.target_vpip),
        "target_pfr": float(config.target_pfr),
        "target_af": float(config.target_af),
        "exploit_weights": config.exploit_weights,
        "max_winrate_cap": float(config.max_winrate_cap) if config.max_winrate_cap else None
    }
    audit_log_create(db, admin_key, "update", "bot_config", config.id, old_values, new_values)
    
    return config


@router.delete("/bot-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot_config(
    config_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Удаляет конфигурацию бота"""
    config = db.query(BotConfig).filter(BotConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot config not found"
        )
    
    audit_log_create(db, admin_key, "delete", "bot_config", config.id, {"bot_id": config.bot_id, "name": config.name}, None)
    
    db.delete(config)
    db.commit()
    
    return None
