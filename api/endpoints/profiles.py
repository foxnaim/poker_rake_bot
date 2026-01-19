"""Endpoints для работы с профилями оппонентов"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.schemas import OpponentProfileResponse, OpponentProfileUpdate, OpponentProfileCreate, OpponentProfileBulkRequest, BulkOperationResponse
from brain.opponent_profiler import opponent_profiler
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["profiles"])


@router.get("/opponent/{opponent_id}", response_model=OpponentProfileResponse)
async def get_opponent_profile(
    opponent_id: str,
    db: Session = Depends(get_db)
):
    """
    Получает профиль оппонента
    
    Возвращает:
    - Статистику (VPIP, PFR, AF, etc.)
    - Классификацию типа игрока
    - Уверенность в классификации
    """
    # Прямой запрос к БД
    from data.models import OpponentProfile
    
    # Ищем профиль напрямую в БД
    # Используем with_for_update для блокировки строки
    profile = db.query(OpponentProfile).filter(
        OpponentProfile.opponent_id == opponent_id
    ).first()
    
    # Если не нашли, пробуем через profiler
    if not profile:
        profile = opponent_profiler.get_profile(opponent_id, db)
    
    if not profile:
        return OpponentProfileResponse(
            opponent_id=opponent_id,
            vpip=0.0,
            pfr=0.0,
            three_bet_pct=0.0,
            aggression_factor=0.0,
            hands_played=0,
            classification="unknown"
        )
    
    return OpponentProfileResponse(
        opponent_id=profile.opponent_id,
        vpip=float(profile.vpip),
        pfr=float(profile.pfr),
        three_bet_pct=float(profile.three_bet_pct),
        aggression_factor=float(profile.aggression_factor),
        hands_played=profile.hands_played,
        classification=profile.classification or "unknown"
    )


@router.get("/opponents", response_model=List[OpponentProfileResponse])
async def get_all_opponents(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=1000, description="Максимум записей"),
    classification: Optional[str] = Query(None, description="Фильтр по типу игрока"),
    min_hands: int = Query(0, ge=0, description="Минимум сыгранных рук"),
    db: Session = Depends(get_db)
):
    """
    Получает список всех профилей оппонентов

    Параметры:
    - skip: пропустить N записей (для пагинации)
    - limit: максимум записей (1-1000)
    - classification: фильтр по типу (fish, nit, tag, lag, calling_station)
    - min_hands: минимальное количество рук
    """
    from data.models import OpponentProfile

    query = db.query(OpponentProfile)

    # Фильтры
    if classification:
        query = query.filter(OpponentProfile.classification == classification)

    if min_hands > 0:
        query = query.filter(OpponentProfile.hands_played >= min_hands)

    # Сортировка по количеству рук (больше данных = надежнее)
    query = query.order_by(OpponentProfile.hands_played.desc())

    # Пагинация
    profiles = query.offset(skip).limit(limit).all()

    return [
        OpponentProfileResponse(
            opponent_id=p.opponent_id,
            vpip=float(p.vpip),
            pfr=float(p.pfr),
            three_bet_pct=float(p.three_bet_pct),
            aggression_factor=float(p.aggression_factor),
            hands_played=p.hands_played,
            classification=p.classification or "unknown"
        )
        for p in profiles
    ]


@router.post("/opponent", response_model=OpponentProfileResponse, status_code=201)
async def create_opponent_profile(
    profile: OpponentProfileCreate,
    db: Session = Depends(get_db)
):
    """
    Создает новый профиль оппонента вручную

    Полезно для импорта профилей или ручной настройки
    """
    from data.models import OpponentProfile

    # Проверяем, не существует ли уже
    existing = db.query(OpponentProfile).filter(
        OpponentProfile.opponent_id == profile.opponent_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Профиль для оппонента {profile.opponent_id} уже существует"
        )

    # Классифицируем на основе stats
    classification = opponent_profiler._classify_player(
        vpip=profile.vpip,
        pfr=profile.pfr,
        three_bet_pct=profile.three_bet_pct,
        aggression_factor=profile.aggression_factor
    )

    new_profile = OpponentProfile(
        opponent_id=profile.opponent_id,
        vpip=profile.vpip,
        pfr=profile.pfr,
        three_bet_pct=profile.three_bet_pct,
        aggression_factor=profile.aggression_factor,
        hands_played=profile.hands_played or 0,
        classification=classification
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return OpponentProfileResponse(
        opponent_id=new_profile.opponent_id,
        vpip=float(new_profile.vpip),
        pfr=float(new_profile.pfr),
        three_bet_pct=float(new_profile.three_bet_pct),
        aggression_factor=float(new_profile.aggression_factor),
        hands_played=new_profile.hands_played,
        classification=new_profile.classification
    )


@router.put("/opponent/{opponent_id}", response_model=OpponentProfileResponse)
async def update_opponent_profile(
    opponent_id: str,
    profile_update: OpponentProfileUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновляет существующий профиль оппонента

    Можно обновить любое поле, не указанные поля останутся без изменений
    """
    from data.models import OpponentProfile

    profile = db.query(OpponentProfile).filter(
        OpponentProfile.opponent_id == opponent_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Профиль для оппонента {opponent_id} не найден"
        )

    # Обновляем только переданные поля
    update_data = profile_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile, field, value)

    # Пересчитываем классификацию если изменились stats
    if any(k in update_data for k in ['vpip', 'pfr', 'three_bet_pct', 'aggression_factor']):
        profile.classification = opponent_profiler._classify_player(
            vpip=profile.vpip,
            pfr=profile.pfr,
            three_bet_pct=profile.three_bet_pct,
            aggression_factor=profile.aggression_factor
        )

    db.commit()
    db.refresh(profile)

    return OpponentProfileResponse(
        opponent_id=profile.opponent_id,
        vpip=float(profile.vpip),
        pfr=float(profile.pfr),
        three_bet_pct=float(profile.three_bet_pct),
        aggression_factor=float(profile.aggression_factor),
        hands_played=profile.hands_played,
        classification=profile.classification
    )


@router.delete("/opponent/{opponent_id}", status_code=204)
async def delete_opponent_profile(
    opponent_id: str,
    db: Session = Depends(get_db)
):
    """
    Удаляет профиль оппонента

    ВНИМАНИЕ: Это действие необратимо!
    """
    from data.models import OpponentProfile

    profile = db.query(OpponentProfile).filter(
        OpponentProfile.opponent_id == opponent_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Профиль для оппонента {opponent_id} не найден"
        )

    db.delete(profile)
    db.commit()

    return None


@router.post("/opponents/bulk", response_model=BulkOperationResponse)
async def create_opponents_bulk(
    request: OpponentProfileBulkRequest,
    db: Session = Depends(get_db)
):
    """
    Массовая загрузка профилей оппонентов

    Полезно для:
    - Импорта профилей из других систем
    - Загрузки архивных данных
    - Миграции баз данных

    Возвращает:
    - Количество успешно загруженных профилей
    - Список ошибок (если были)
    """
    from data.models import OpponentProfile

    success_count = 0
    updated_count = 0
    errors = []

    for idx, profile_data in enumerate(request.profiles):
        try:
            # Проверяем существует ли уже
            existing = db.query(OpponentProfile).filter(
                OpponentProfile.opponent_id == profile_data.opponent_id
            ).first()

            if existing:
                if request.update_existing:
                    # Обновляем существующий
                    existing.vpip = profile_data.vpip
                    existing.pfr = profile_data.pfr
                    existing.three_bet_pct = profile_data.three_bet_pct
                    existing.aggression_factor = profile_data.aggression_factor
                    existing.hands_played = profile_data.hands_played or 0

                    # Пересчитываем классификацию
                    existing.classification = opponent_profiler._classify_player(
                        vpip=existing.vpip,
                        pfr=existing.pfr,
                        three_bet_pct=existing.three_bet_pct,
                        aggression_factor=existing.aggression_factor
                    )

                    updated_count += 1
                elif not request.skip_existing:
                    errors.append({
                        "index": idx,
                        "opponent_id": profile_data.opponent_id,
                        "error": "Profile already exists"
                    })
                continue

            # Создаем новый профиль
            classification = opponent_profiler._classify_player(
                vpip=profile_data.vpip,
                pfr=profile_data.pfr,
                three_bet_pct=profile_data.three_bet_pct,
                aggression_factor=profile_data.aggression_factor
            )

            new_profile = OpponentProfile(
                opponent_id=profile_data.opponent_id,
                vpip=profile_data.vpip,
                pfr=profile_data.pfr,
                three_bet_pct=profile_data.three_bet_pct,
                aggression_factor=profile_data.aggression_factor,
                hands_played=profile_data.hands_played or 0,
                classification=classification
            )

            db.add(new_profile)
            success_count += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "opponent_id": profile_data.opponent_id,
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
        "total_requested": len(request.profiles),
        "created": success_count,
        "updated": updated_count,
        "failed": len(errors),
        "errors": errors if errors else None
    }
