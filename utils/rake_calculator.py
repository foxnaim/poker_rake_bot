"""Калькулятор рейка на основе моделей room+limit"""

from typing import Optional
from sqlalchemy.orm import Session
from decimal import Decimal

from data.models import RakeModel, Table, Room


def calculate_rake(
    pot_size: float,
    room_id: Optional[int],
    limit_type: str,
    db: Session
) -> float:
    """
    Вычисляет рейк на основе модели room+limit
    
    Args:
        pot_size: Размер пота
        room_id: ID комнаты (опционально, если None - ищем по limit_type)
        limit_type: Лимит (NL10, NL50, etc.)
        db: Сессия БД
        
    Returns:
        Размер рейка
    """
    # Если pot меньше минимального, рейк = 0
    if pot_size <= 0:
        return 0.0
    
    # Ищем модель рейка
    rake_model = None
    
    if room_id:
        # Сначала ищем по room_id + limit_type
        rake_model = db.query(RakeModel).filter(
            RakeModel.room_id == room_id,
            RakeModel.limit_type == limit_type
        ).first()
        
        # Если не нашли, ищем по room_id (для всех лимитов)
        if not rake_model:
            rake_model = db.query(RakeModel).filter(
                RakeModel.room_id == room_id,
                RakeModel.limit_type.is_(None)
            ).first()
    
    # Если не нашли по room_id, ищем только по limit_type (глобальная модель)
    if not rake_model:
        rake_model = db.query(RakeModel).filter(
            RakeModel.room_id.is_(None),
            RakeModel.limit_type == limit_type
        ).first()
    
    # Если модель не найдена, используем дефолтные значения
    if not rake_model:
        # Дефолтная модель: 5% рейк, кап 3.00
        percent = Decimal('5.00')
        cap = Decimal('3.00')
        min_pot = Decimal('0.00')
    else:
        percent = rake_model.percent
        cap = rake_model.cap
        min_pot = rake_model.min_pot or Decimal('0.00')
    
    # Проверяем минимальный пот
    if pot_size < float(min_pot):
        return 0.0
    
    # Вычисляем рейк: процент от пота
    rake = float(pot_size) * float(percent) / 100.0
    
    # Применяем кап (если есть)
    if cap is not None:
        rake = min(rake, float(cap))
    
    return round(rake, 2)


def get_rake_model(
    room_id: Optional[int],
    limit_type: str,
    db: Session
) -> Optional[RakeModel]:
    """
    Получает модель рейка для room+limit
    
    Returns:
        RakeModel или None
    """
    if room_id:
        # Сначала ищем по room_id + limit_type
        rake_model = db.query(RakeModel).filter(
            RakeModel.room_id == room_id,
            RakeModel.limit_type == limit_type
        ).first()
        
        if rake_model:
            return rake_model
        
        # Если не нашли, ищем по room_id (для всех лимитов)
        rake_model = db.query(RakeModel).filter(
            RakeModel.room_id == room_id,
            RakeModel.limit_type.is_(None)
        ).first()
        
        if rake_model:
            return rake_model
    
    # Ищем только по limit_type (глобальная модель)
    return db.query(RakeModel).filter(
        RakeModel.room_id.is_(None),
        RakeModel.limit_type == limit_type
    ).first()
