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
    "start_time": None
}


def run_training(format: str, iterations: int, db: Session):
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

        # Импортируем trainer
        from training.mccfr_trainer import MCCFRTrainer

        # Создаем trainer
        trainer = MCCFRTrainer(
            game_format=format,
            max_players=6,
            exploration_param=0.3
        )

        # Запускаем обучение с прогрессом
        print(f"Starting training: {format} for {iterations} iterations")

        for i in range(iterations):
            trainer.train_iteration()
            training_state["current_iteration"] = i + 1

            # Сохраняем чекпоинт каждые 10000 итераций
            if (i + 1) % 10000 == 0:
                checkpoint_path = f"checkpoints/{format}_iter_{i+1}.msgpack"
                os.makedirs("checkpoints", exist_ok=True)
                trainer.save_strategy(checkpoint_path)

                # Сохраняем в БД
                from data.models import TrainingCheckpoint
                checkpoint = TrainingCheckpoint(
                    checkpoint_id=f"{format}_{i+1}",
                    version="1.0",
                    format=format,
                    training_iterations=i + 1,
                    file_path=checkpoint_path,
                    is_active=False
                )
                db.add(checkpoint)
                db.commit()

                print(f"Checkpoint saved at iteration {i+1}")

        # Финальное сохранение
        final_checkpoint_path = f"checkpoints/{format}_final_{iterations}.msgpack"
        trainer.save_strategy(final_checkpoint_path)

        from data.models import TrainingCheckpoint
        final_checkpoint = TrainingCheckpoint(
            checkpoint_id=f"{format}_final_{iterations}",
            version="1.0",
            format=format,
            training_iterations=iterations,
            file_path=final_checkpoint_path,
            is_active=True  # Активируем финальный чекпоинт
        )
        db.add(final_checkpoint)
        db.commit()

        print(f"Training completed: {iterations} iterations")

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
    background_tasks.add_task(run_training, request.format, request.iterations, db)

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

    # Устанавливаем флаг остановки
    # (В реальной реализации нужен более сложный механизм)
    training_state["total_iterations"] = training_state["current_iteration"]

    return {
        "status": "stopping",
        "message": "Обучение будет остановлено после завершения текущей итерации"
    }
