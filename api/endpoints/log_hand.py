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
from datetime import datetime, timezone
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["hands"])


def _canonical_table_id(db: Session, table_id_in: Optional[str]) -> Optional[str]:
    """
    Приводит входной table_id к каноническому table_key (Table.external_table_id), если возможно.
    Если не удалось — возвращает исходное значение (как строку).
    """
    if not table_id_in:
        return None

    from data.models import Table

    table_id_str = str(table_id_in)
    table = None

    # 1) internal PK (если прилетело число)
    try:
        pk = int(table_id_str)
    except (TypeError, ValueError):
        pk = None
    if pk is not None:
        table = db.query(Table).filter(Table.id == pk).first()

    # 2) external_table_id
    if table is None:
        table = db.query(Table).filter(Table.external_table_id == table_id_str).first()

    if table and table.external_table_id:
        return table.external_table_id

    return table_id_str


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
        table_id_in = getattr(request, "table_key", None) or request.table_id
        canonical_table_id = _canonical_table_id(db, table_id_in)

        # Вычисляем рейк по модели (если не передан явно)
        # Если rake_amount передан, используем его, иначе вычисляем
        calculated_rake = request.rake_amount
        if calculated_rake is None or calculated_rake == 0:
            # Получаем room_id из table_id через Table (по internal id или external_table_id)
            room_id = None
            if table_id_in:
                from data.models import Table
                table = None
                # 1) internal PK (если прилетел int)
                try:
                    table_pk = int(str(table_id_in))
                except (TypeError, ValueError):
                    table_pk = None
                if table_pk is not None:
                    table = db.query(Table).filter(Table.id == table_pk).first()
                # 2) external_table_id (если PK не подошёл)
                if table is None:
                    table = db.query(Table).filter(Table.external_table_id == str(table_id_in)).first()
                if table:
                    room_id = table.room_id

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
        existing = db.query(Hand).filter(Hand.hand_id == request.hand_id).first()
        if existing:
            # idempotent update (полезно для тестов/повторной загрузки логов)
            existing.table_id = canonical_table_id or str(table_id_in)
            existing.limit_type = request.limit_type
            existing.session_id = session_id_int
            existing.players_count = request.players_count
            existing.hero_position = request.hero_position
            existing.hero_cards = request.hero_cards
            existing.board_cards = request.board_cards or ""
            existing.pot_size = request.pot_size
            existing.rake_amount = calculated_rake
            existing.hero_result = request.hero_result
            existing.hand_history = request.hand_history
            existing.timestamp = datetime.now(timezone.utc)
            db.commit()
        else:
            hand = Hand(
                hand_id=request.hand_id,
                table_id=canonical_table_id or str(table_id_in),
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
                timestamp=datetime.now(timezone.utc)
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
            "table_key": canonical_table_id or str(table_id_in),
            "pot_size": request.pot_size,
            "hero_result": request.hero_result,
            "limit_type": request.limit_type
        })
        
        return {"status": "logged", "hand_id": request.hand_id, "table_key": canonical_table_id or str(table_id_in)}

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

            table_id_in = getattr(hand_data, "table_key", None) or hand_data.table_id
            canonical_table_id = _canonical_table_id(db, table_id_in)

            # Вычисляем рейк по модели (если не передан явно)
            calculated_rake = hand_data.rake_amount
            if calculated_rake is None or calculated_rake == 0:
                # Получаем room_id из table_id через Table (по internal id или external_table_id)
                room_id = None
                if table_id_in:
                    from data.models import Table
                    table = None
                    try:
                        table_pk = int(str(table_id_in))
                    except (TypeError, ValueError):
                        table_pk = None
                    if table_pk is not None:
                        table = db.query(Table).filter(Table.id == table_pk).first()
                    if table is None:
                        table = db.query(Table).filter(Table.external_table_id == str(table_id_in)).first()
                    if table:
                        room_id = table.room_id

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
                table_id=canonical_table_id or str(table_id_in),
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
                timestamp=datetime.now(timezone.utc)
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
