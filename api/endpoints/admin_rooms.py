"""Admin endpoints для управления комнатами"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from data.database import get_db
from data.models import Room, Table
from api.auth import require_admin
from api.audit import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "rooms"])


class RoomCreate(BaseModel):
    """Создание комнаты"""
    room_link: str
    type: str  # pokerstars, ggpoker, acr, etc.
    status: str = "pending"
    meta: Optional[dict] = None


class RoomUpdate(BaseModel):
    """Обновление комнаты"""
    room_link: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    rake_model_id: Optional[int] = None
    meta: Optional[dict] = None


class RoomResponse(BaseModel):
    """Ответ с комнатой"""
    id: int
    room_link: str
    type: str
    status: str
    rake_model_id: Optional[int]
    meta: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomOnboardRequest(BaseModel):
    """Onboarding комнаты"""
    room_link: str
    type: str
    meta: Optional[dict] = None


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Создает новую комнату"""
    existing = db.query(Room).filter(Room.room_link == request.room_link).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room with link '{request.room_link}' already exists"
        )
    
    room = Room(
        room_link=request.room_link,
        type=request.type,
        status=request.status,
        meta=request.meta
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    audit_log_create(db, admin_key, "create", "room", room.id, None, {"room_link": room.room_link})
    
    return room


@router.post("/rooms/onboard", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def onboard_room(
    request: RoomOnboardRequest,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Onboarding новой комнаты (создание со статусом onboarded)"""
    existing = db.query(Room).filter(Room.room_link == request.room_link).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room with link '{request.room_link}' already exists"
        )
    
    room = Room(
        room_link=request.room_link,
        type=request.type,
        status="onboarded",
        meta=request.meta
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    audit_log_create(db, admin_key, "onboard", "room", room.id, None, {"room_link": room.room_link})
    
    return room


@router.get("/rooms", response_model=List[RoomResponse])
async def list_rooms(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Список всех комнат"""
    query = db.query(Room)
    
    if status_filter:
        query = query.filter(Room.status == status_filter)
    if type_filter:
        query = query.filter(Room.type == type_filter)
    
    rooms = query.order_by(Room.created_at.desc()).all()
    return rooms


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает комнату по ID"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    return room


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    request: RoomUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Обновляет комнату"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    old_values = {
        "room_link": room.room_link,
        "type": room.type,
        "status": room.status,
        "rake_model_id": room.rake_model_id
    }
    
    if request.room_link is not None:
        existing = db.query(Room).filter(Room.room_link == request.room_link, Room.id != room_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room with link '{request.room_link}' already exists"
            )
        room.room_link = request.room_link
    
    if request.type is not None:
        room.type = request.type
    if request.status is not None:
        room.status = request.status
    if request.rake_model_id is not None:
        room.rake_model_id = request.rake_model_id
    if request.meta is not None:
        room.meta = request.meta
    
    db.commit()
    db.refresh(room)
    
    new_values = {
        "room_link": room.room_link,
        "type": room.type,
        "status": room.status,
        "rake_model_id": room.rake_model_id
    }
    audit_log_create(db, admin_key, "update", "room", room.id, old_values, new_values)
    
    return room


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Удаляет комнату"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    audit_log_create(db, admin_key, "delete", "room", room.id, {"room_link": room.room_link}, None)
    
    db.delete(room)
    db.commit()
    
    return None
