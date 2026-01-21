"""Endpoint для логирования раздач"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.schemas import HandLogRequest, HandLogBulkRequest, HandLogResponse, BulkOperationResponse
from api.auth import optional_api_key
from data.models import Hand
from data.database import get_db
from api.websocket import broadcast_hand_result
from brain.opponent_profiler import opponent_profiler
from utils.rake_calculator import calculate_rake
from datetime import datetime
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["hands"])


@router.post("/log_hand", response_model=HandLogResponse)
async def log_hand_endpoint(
    request: HandLogRequest,
    db: Session = Depends(get_db),
    api_key_valid: bool = Depends(optional_api_key)
):
    """
    Логирует завершенную раздачу
    
    Обновляет:
    - Таблицу hands
    - Профили оппонентов (через Opponent Profiler)
    """
    try:
        # Вычисляем рейк по модели (если не передан явно)
        # Если rake_amount передан, используем его, иначе вычисляем
        calculated_rake = request.rake_amount
        if calculated_rake is None or calculated_rake == 0:
            # Получаем room_id из table_id (если возможно)
            # Для упрощения используем только limit_type
            room_id = None  # TODO: получать room_id из table_id через Table
            calculated_rake = calculate_rake(
                pot_size=request.pot_size,
                room_id=room_id,
                limit_type=request.limit_type,
                db=db
            )
        
        # Получаем session_id из строки (если передан)
        session_id_int = None
        if request.session_id:
            from data.models import BotSession
            session = db.query(BotSession).filter(BotSession.session_id == request.session_id).first()
            if session:
                session_id_int = session.id
        
        # Сохраняем раздачу
        hand = Hand(
            hand_id=request.hand_id,
            table_id=request.table_id,
            limit_type=request.limit_type,
            session_id=session_id_int,
            players_count=request.players_count,
            hero_position=request.hero_position,
            hero_cards=request.hero_cards,
            board_cards=request.board_cards or "",
            pot_size=request.pot_size,
            rake_amount=calculated_rake,
            hero_result=request.hero_result,
            hand_history=request.hand_history,
            timestamp=datetime.utcnow()
        )
        
        db.add(hand)
        db.commit()
        
        # Обновляем метрики сессий (если есть активная сессия)
        from data.models import BotStats
        active_session = db.query(BotStats).filter(
            BotStats.limit_type == request.limit_type,
            BotStats.period_end.is_(None)
        ).order_by(BotStats.period_start.desc()).first()
        
        if active_session:
            from api.metrics import session_hands_total, session_profit_total, session_rake_total
            session_hands_total.labels(session_id=active_session.session_id, limit_type=request.limit_type).inc()
            session_profit_total.labels(session_id=active_session.session_id, limit_type=request.limit_type).inc(float(request.hero_result))
            session_rake_total.labels(session_id=active_session.session_id, limit_type=request.limit_type).inc(float(calculated_rake))
        
        # Обновляем профили оппонентов
        if request.hand_history:
            for opponent_id, opponent_data in request.hand_history.items():
                if isinstance(opponent_data, dict):
                    opponent_profiler.update_profile(
                        opponent_id,
                        opponent_data,
                        db
                    )
        
        # Отправляем через WebSocket
        await broadcast_hand_result({
            "hand_id": request.hand_id,
            "pot_size": request.pot_size,
            "hero_result": request.hero_result,
            "limit_type": request.limit_type
        })
        
        return {"status": "logged", "hand_id": request.hand_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hands/bulk", response_model=BulkOperationResponse)
async def log_hands_bulk(
    request: HandLogBulkRequest,
    db: Session = Depends(get_db),
    api_key_valid: bool = Depends(optional_api_key)
):
    """
    Массовая загрузка раздач

    Полезно для:
    - Импорта hand history из файлов
    - Загрузки архивных данных
    - Миграции с других систем

    Возвращает:
    - Количество успешно загруженных раздач
    - Список ошибок (если были)
    """
    success_count = 0
    errors = []

    for idx, hand_data in enumerate(request.hands):
        try:
            # Проверяем существует ли уже
            existing = db.query(Hand).filter(Hand.hand_id == hand_data.hand_id).first()
            if existing:
                if not request.skip_existing:
                    errors.append({
                        "index": idx,
                        "hand_id": hand_data.hand_id,
                        "error": "Hand already exists"
                    })
                continue

            # Вычисляем рейк по модели (если не передан явно)
            calculated_rake = hand_data.rake_amount
            if calculated_rake is None or calculated_rake == 0:
                room_id = None  # TODO: получать room_id из table_id
                calculated_rake = calculate_rake(
                    pot_size=hand_data.pot_size,
                    room_id=room_id,
                    limit_type=hand_data.limit_type,
                    db=db
                )
            
            # Получаем session_id (если передан)
            session_id_int = None
            if hasattr(hand_data, 'session_id') and hand_data.session_id:
                from data.models import BotSession
                session = db.query(BotSession).filter(BotSession.session_id == hand_data.session_id).first()
                if session:
                    session_id_int = session.id
            
            # Создаем раздачу
            hand = Hand(
                hand_id=hand_data.hand_id,
                table_id=hand_data.table_id,
                limit_type=hand_data.limit_type,
                session_id=session_id_int,
                players_count=hand_data.players_count,
                hero_position=hand_data.hero_position,
                hero_cards=hand_data.hero_cards,
                board_cards=hand_data.board_cards or "",
                pot_size=hand_data.pot_size,
                rake_amount=calculated_rake,
                hero_result=hand_data.hero_result,
                hand_history=hand_data.hand_history,
                timestamp=datetime.utcnow()
            )

            db.add(hand)
            success_count += 1

            # Обновляем профили оппонентов
            if hand_data.hand_history:
                for opponent_id, opponent_data in hand_data.hand_history.items():
                    if isinstance(opponent_data, dict):
                        try:
                            opponent_profiler.update_profile(
                                opponent_id,
                                opponent_data,
                                db
                            )
                        except Exception as e:
                            # Логируем но не прерываем процесс
                            print(f"Error updating opponent {opponent_id}: {e}")

        except Exception as e:
            errors.append({
                "index": idx,
                "hand_id": hand_data.hand_id,
                "error": str(e)
            })

    # Сохраняем все успешные в одной транзакции
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to commit bulk insert: {str(e)}"
        )

    return {
        "status": "completed",
        "total_requested": len(request.hands),
        "successful": success_count,
        "failed": len(errors),
        "errors": errors if errors else None
    }
