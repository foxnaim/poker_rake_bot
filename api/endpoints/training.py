"""Endpoints для управления обучением"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import asyncio
import os

from api.schemas import TrainingStart, TrainingStatus, TrainingStartResponse, TrainingStopResponse
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["training"])

# Глобальное состояние обучения
training_state = {
    "is_running": False,
    "current_iteration": 0,
    "total_iterations": 0,
    "format": None,
    "start_time": None,
    "stop_requested": False
}


def run_training(format: str, iterations: int, checkpoint_interval: int = 2000):
    """
    Запускает обучение в фоновом режиме
    """
    global training_state

    try:
        training_state["is_running"] = True
        training_state["current_iteration"] = 0
        training_state["total_iterations"] = iterations
        training_state["format"] = format
        training_state["start_time"] = datetime.utcnow()
        training_state["stop_requested"] = False

        # Реальный training pipeline проекта: MCCFR + GameTree + save_checkpoint (pickle)
        from pathlib import Path
        from brain.game_tree import GameTree
        from brain.mccfr import MCCFR
        from data.database import SessionLocal, init_db
        from data.models import TrainingCheckpoint
        from training.train_mccfr import save_checkpoint

        init_db()

        max_raise_sizes = {
            0: 2,  # PREFLOP
            1: 2,  # FLOP
            2: 3,  # TURN
            3: 3   # RIVER
        }

        game_tree = GameTree(max_raise_sizes=max_raise_sizes)
        mccfr = MCCFR(game_tree, num_players=2)

        checkpoint_dir = Path("checkpoints") / format
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        print(f"Starting training (MCCFR): {format} for {iterations} iterations")

        iterations_done = 0
        while iterations_done < iterations:
            if training_state.get("stop_requested"):
                print("Training stop requested.")
                break

            batch = min(checkpoint_interval, iterations - iterations_done)
            mccfr.train(batch, verbose=True)
            iterations_done += batch
            training_state["current_iteration"] = iterations_done

            # Сохраняем чекпоинт (и запись в БД делается внутри save_checkpoint)
            checkpoint_path = save_checkpoint(
                mccfr=mccfr,
                game_tree=game_tree,
                format_type=format,
                iteration=iterations_done,
                checkpoint_dir=checkpoint_dir
            )
            print(f"Checkpoint saved: {checkpoint_path}")

        # Активируем последний чекпоинт этого формата
        db = SessionLocal()
        try:
            last_checkpoint = db.query(TrainingCheckpoint).filter(
                TrainingCheckpoint.format == format
            ).order_by(TrainingCheckpoint.created_at.desc()).first()
            if last_checkpoint:
                db.query(TrainingCheckpoint).filter(
                    TrainingCheckpoint.format == format
                ).update({"is_active": False})
                last_checkpoint.is_active = True
                db.commit()
                print(f"Activated checkpoint: {last_checkpoint.checkpoint_id}")
        finally:
            db.close()

    except Exception as e:
        print(f"Training error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        training_state["is_running"] = False
        training_state["current_iteration"] = 0
        training_state["total_iterations"] = 0
        training_state["format"] = None
        training_state["start_time"] = None
        training_state["stop_requested"] = False


@router.post("/training/start", response_model=TrainingStartResponse)
async def start_training(
    request: TrainingStart,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Запускает обучение MCCFR в фоновом режиме

    Параметры:
    - format: формат игры (NL10, NL25, etc.)
    - iterations: количество итераций (1000-1000000)
    - checkpoint_version: опционально, версия чекпоинта для продолжения

    ВАЖНО: Обучение запускается асинхронно!
    Используйте GET /training/status для мониторинга прогресса
    """
    global training_state

    if training_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="Обучение уже запущено. Дождитесь завершения или остановите текущий процесс."
        )

    # Проверяем валидность формата
    valid_formats = ["NL10", "NL25", "NL50", "NL100", "NL200"]
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Неверный формат. Доступны: {', '.join(valid_formats)}"
        )

    # Запускаем обучение в фоновом режиме
    background_tasks.add_task(run_training, request.format, request.iterations)

    return {
        "status": "started",
        "format": request.format,
        "iterations": request.iterations,
        "message": "Обучение запущено в фоновом режиме. Используйте GET /training/status для мониторинга."
    }


@router.get("/training/status", response_model=TrainingStatus)
async def get_training_status():
    """
    Получает текущий статус обучения

    Возвращает:
    - is_running: запущено ли обучение
    - current_iteration: текущая итерация
    - total_iterations: всего итераций
    - format: формат игры
    - start_time: время начала
    - estimated_completion: примерное время завершения
    """
    global training_state

    estimated_completion = None
    if training_state["is_running"] and training_state["current_iteration"] > 0:
        elapsed = (datetime.utcnow() - training_state["start_time"]).total_seconds()
        iterations_left = training_state["total_iterations"] - training_state["current_iteration"]
        time_per_iteration = elapsed / training_state["current_iteration"]
        seconds_left = iterations_left * time_per_iteration

        from datetime import timedelta
        estimated_completion = datetime.utcnow() + timedelta(seconds=seconds_left)

    return TrainingStatus(
        is_running=training_state["is_running"],
        current_iteration=training_state["current_iteration"] if training_state["is_running"] else None,
        total_iterations=training_state["total_iterations"] if training_state["is_running"] else None,
        format=training_state["format"],
        start_time=training_state["start_time"],
        estimated_completion=estimated_completion
    )


@router.post("/training/stop", response_model=TrainingStopResponse)
async def stop_training():
    """
    Останавливает текущее обучение

    ВНИМАНИЕ: Остановка может занять время (до завершения текущей итерации)
    """
    global training_state

    if not training_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="Обучение не запущено"
        )

    # Просим корректно остановиться на границе батча
    training_state["stop_requested"] = True

    return {
        "status": "stopping",
        "message": "Обучение будет остановлено после завершения текущей итерации"
    }
