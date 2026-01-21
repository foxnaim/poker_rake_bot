"""Admin endpoints для управления столами"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from data.database import get_db
from data.models import Table, Room
from api.auth import require_admin
from api.audit import audit_log_create

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "tables"])


class TableCreate(BaseModel):
    """Создание стола"""
    room_id: int
    # для UI/агента: строковый ключ стола (например "table_1", "pp_123")
    table_key: Optional[str] = None
    # backward-compat: если кто-то уже шлёт external_table_id
    external_table_id: Optional[str] = None
    limit_type: str
    max_players: int = 6
    meta: Optional[dict] = None


class TableUpdate(BaseModel):
    """Обновление стола"""
    table_key: Optional[str] = None
    external_table_id: Optional[str] = None
    limit_type: Optional[str] = None
    max_players: Optional[int] = None
    meta: Optional[dict] = None


class TableResponse(BaseModel):
    """Ответ со столом"""
    id: int
    room_id: int
    table_key: Optional[str]
    limit_type: str
    max_players: int
    meta: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/tables", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    request: TableCreate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Создает новый стол"""
    # Проверяем существование комнаты
    room = db.query(Room).filter(Room.id == request.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Проверяем уникальность room_id + limit_type
    existing = db.query(Table).filter(
        Table.room_id == request.room_id,
        Table.limit_type == request.limit_type
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Table with limit '{request.limit_type}' already exists for this room"
        )
    
    # Проверяем уникальность table_key (external_table_id) в рамках комнаты
    table_key = request.table_key or request.external_table_id
    if table_key:
        existing_key = db.query(Table).filter(
            Table.room_id == request.room_id,
            Table.external_table_id == table_key
        ).first()
        if existing_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table with table_key '{table_key}' already exists for this room"
            )

    table = Table(
        room_id=request.room_id,
        external_table_id=(request.table_key or request.external_table_id),
        limit_type=request.limit_type,
        max_players=request.max_players,
        meta=request.meta
    )
    
    db.add(table)
    db.commit()
    db.refresh(table)
    
    audit_log_create(db, admin_key, "create", "table", table.id, None, {"room_id": table.room_id, "limit_type": table.limit_type})
    
    return table


@router.get("/tables", response_model=List[TableResponse])
async def list_tables(
    room_id: Optional[int] = None,
    limit_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Список всех столов"""
    query = db.query(Table)
    
    if room_id:
        query = query.filter(Table.room_id == room_id)
    if limit_type:
        query = query.filter(Table.limit_type == limit_type)
    
    tables = query.order_by(Table.created_at.desc()).all()
    return tables


@router.get("/tables/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Получает стол по ID"""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    return table


@router.patch("/tables/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: int,
    request: TableUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Обновляет стол"""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    old_values = {
        "table_key": table.external_table_id,
        "limit_type": table.limit_type,
        "max_players": table.max_players
    }
    
    if request.table_key is not None or request.external_table_id is not None:
        new_key = request.table_key or request.external_table_id
        # Уникальность в рамках комнаты
        if new_key:
            existing_key = db.query(Table).filter(
                Table.room_id == table.room_id,
                Table.external_table_id == new_key,
                Table.id != table_id
            ).first()
            if existing_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table with table_key '{new_key}' already exists for this room"
                )
        table.external_table_id = new_key
    if request.limit_type is not None:
        # Проверяем уникальность
        existing = db.query(Table).filter(
            Table.room_id == table.room_id,
            Table.limit_type == request.limit_type,
            Table.id != table_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table with limit '{request.limit_type}' already exists for this room"
            )
        table.limit_type = request.limit_type
    
    if request.max_players is not None:
        table.max_players = request.max_players
    if request.meta is not None:
        table.meta = request.meta
    
    db.commit()
    db.refresh(table)
    
    new_values = {
        "table_key": table.external_table_id,
        "limit_type": table.limit_type,
        "max_players": table.max_players
    }
    audit_log_create(db, admin_key, "update", "table", table.id, old_values, new_values)
    
    return table


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    admin_key: str = Depends(require_admin)
):
    """Удаляет стол"""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    audit_log_create(db, admin_key, "delete", "table", table.id, {"room_id": table.room_id, "limit_type": table.limit_type}, None)
    
    db.delete(table)
    db.commit()
    
    return None
