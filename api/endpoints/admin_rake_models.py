"""Admin endpoints для управления моделями рейка"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from data.database import get_db
from data.models import RakeModel, Room
from api.auth import require_admin
from api.schemas import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "rake-models"])


class RakeModelCreate(BaseModel):
    """Создание модели рейка"""
    room_id: Optional[int] = None
    limit_type: Optional[str] = None
    percent: float
    cap: Optional[float] = None
    min_pot: float = 0
    params: Optional[dict] = None


class RakeModelUpdate(BaseModel):
    """Обновление модели рейка"""
    percent: Optional[float] = None
    cap: Optional[float] = None
    min_pot: Optional[float] = None
    params: Optional[dict] = None


class RakeModelResponse(BaseModel):
    """Ответ с моделью рейка"""
    id: int
    room_id: Optional[int]
    limit_type: Optional[str]
    percent: float
    cap: Optional[float]
    min_pot: Optional[float]
    params: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/rake-models", response_model=RakeModelResponse, status_code=status.HTTP_201_CREATED)
async def create_rake_model(
    request: RakeModelCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Создает новую модель рейка"""
    # Проверяем комнату если указана
    if request.room_id:
        room = db.query(Room).filter(Room.id == request.room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
    
    # Проверяем уникальность room_id + limit_type
    existing = db.query(RakeModel).filter(
        RakeModel.room_id == request.room_id,
        RakeModel.limit_type == request.limit_type
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rake model already exists for this room and limit"
        )
    
    rake_model = RakeModel(
        room_id=request.room_id,
        limit_type=request.limit_type,
        percent=request.percent,
        cap=request.cap,
        min_pot=request.min_pot,
        params=request.params
    )
    
    db.add(rake_model)
    db.commit()
    db.refresh(rake_model)
    
    audit_log_create(db, admin_key, "create", "rake_model", rake_model.id, None, {"room_id": rake_model.room_id, "limit_type": rake_model.limit_type})
    
    return rake_model


@router.get("/rake-models", response_model=List[RakeModelResponse])
async def list_rake_models(
    room_id: Optional[int] = None,
    limit_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Список всех моделей рейка"""
    query = db.query(RakeModel)
    
    if room_id:
        query = query.filter(RakeModel.room_id == room_id)
    if limit_type:
        query = query.filter(RakeModel.limit_type == limit_type)
    
    models = query.order_by(RakeModel.created_at.desc()).all()
    return models


@router.get("/rake-models/{model_id}", response_model=RakeModelResponse)
async def get_rake_model(
    model_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает модель рейка по ID"""
    model = db.query(RakeModel).filter(RakeModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rake model not found"
        )
    return model


@router.patch("/rake-models/{model_id}", response_model=RakeModelResponse)
async def update_rake_model(
    model_id: int,
    request: RakeModelUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Обновляет модель рейка"""
    model = db.query(RakeModel).filter(RakeModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rake model not found"
        )
    
    old_values = {
        "percent": float(model.percent),
        "cap": float(model.cap) if model.cap else None,
        "min_pot": float(model.min_pot) if model.min_pot else None
    }
    
    if request.percent is not None:
        model.percent = request.percent
    if request.cap is not None:
        model.cap = request.cap
    if request.min_pot is not None:
        model.min_pot = request.min_pot
    if request.params is not None:
        model.params = request.params
    
    db.commit()
    db.refresh(model)
    
    new_values = {
        "percent": float(model.percent),
        "cap": float(model.cap) if model.cap else None,
        "min_pot": float(model.min_pot) if model.min_pot else None
    }
    audit_log_create(db, admin_key, "update", "rake_model", model.id, old_values, new_values)
    
    return model


@router.delete("/rake-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rake_model(
    model_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Удаляет модель рейка"""
    model = db.query(RakeModel).filter(RakeModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rake model not found"
        )
    
    audit_log_create(db, admin_key, "delete", "rake_model", model.id, {"room_id": model.room_id, "limit_type": model.limit_type}, None)
    
    db.delete(model)
    db.commit()
    
    return None
