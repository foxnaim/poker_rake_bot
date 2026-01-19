"""Endpoint для логирования раздач"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.schemas import HandLogRequest, HandLogBulkRequest, HandLogResponse, BulkOperationResponse
from api.auth import optional_api_key
from data.models import Hand
from data.database import get_db
from api.websocket import broadcast_hand_result
from brain.opponent_profiler import opponent_profiler
from datetime import datetime
from typing import List

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
        # Сохраняем раздачу
        hand = Hand(
            hand_id=request.hand_id,
            table_id=request.table_id,
            limit_type=request.limit_type,
            players_count=request.players_count,
            hero_position=request.hero_position,
            hero_cards=request.hero_cards,
            board_cards=request.board_cards or "",
            pot_size=request.pot_size,
            rake_amount=request.rake_amount,
            hero_result=request.hero_result,
            hand_history=request.hand_history,
            timestamp=datetime.utcnow()
        )
        
        db.add(hand)
        db.commit()
        
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

            # Создаем раздачу
            hand = Hand(
                hand_id=hand_data.hand_id,
                table_id=hand_data.table_id,
                limit_type=hand_data.limit_type,
                players_count=hand_data.players_count,
                hero_position=hand_data.hero_position,
                hero_cards=hand_data.hero_cards,
                board_cards=hand_data.board_cards or "",
                pot_size=hand_data.pot_size,
                rake_amount=hand_data.rake_amount,
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
