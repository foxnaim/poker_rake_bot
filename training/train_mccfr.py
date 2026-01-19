"""Скрипт обучения MCCFR"""

import argparse
import pickle
import json
import os
from datetime import datetime
from pathlib import Path
import multiprocessing as mp
from typing import Dict

from brain.game_tree import GameTree
from brain.mccfr import MCCFR
from data.database import SessionLocal, init_db
from data.models import TrainingCheckpoint


def train_worker(args):
    """Worker процесс для обучения"""
    iterations, checkpoint_interval, format_type = args
    
    # Создаем дерево игры и MCCFR
    max_raise_sizes = {
        0: 2,  # PREFLOP: 2 размера
        1: 2,  # FLOP: 2 размера
        2: 3,  # TURN: 3 размера
        3: 3   # RIVER: 3 размера
    }
    
    game_tree = GameTree(max_raise_sizes=max_raise_sizes)
    mccfr = MCCFR(game_tree, num_players=2)  # Начинаем с 2 игроков
    
    # Обучение
    mccfr.train(iterations, verbose=False)
    
    # Сохраняем чекпоинт
    checkpoint_data = {
        'game_tree': game_tree,
        'mccfr': mccfr,
        'iterations': mccfr.iterations,
        'regret_history': mccfr.regret_history
    }
    
    return checkpoint_data


def save_checkpoint(mccfr: MCCFR, game_tree: GameTree, format_type: str, 
                   iteration: int, checkpoint_dir: Path):
    """Сохраняет чекпоинт обучения"""
    checkpoint_id = f"mccfr_{format_type}_{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    checkpoint_path = checkpoint_dir / f"{checkpoint_id}.pkl"
    
    # Сохраняем в файл (включаем mccfr объект для дообучения)
    checkpoint_data = {
        'game_tree': game_tree,
        'mccfr': mccfr,  # Сохраняем полный объект для дообучения
        'mccfr_iterations': mccfr.iterations,
        'regret_history': mccfr.regret_history,
        'format_type': format_type,
        'iteration': iteration
    }
    
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(checkpoint_data, f)
    
    # Сохраняем метаданные в БД
    db = SessionLocal()
    try:
        checkpoint = TrainingCheckpoint(
            checkpoint_id=checkpoint_id,
            version="1.0",
            format=format_type,
            training_iterations=mccfr.iterations,
            mccfr_config={
                'max_raise_sizes': game_tree.max_raise_sizes,
                'num_players': mccfr.num_players
            },
            metrics={
                'avg_regret': mccfr.regret_history[-1] if mccfr.regret_history else 0.0,
                'total_nodes': len(game_tree.nodes)
            },
            file_path=str(checkpoint_path),
            is_active=False
        )
        db.add(checkpoint)
        db.commit()
    except Exception as e:
        print(f"Ошибка при сохранении чекпоинта в БД: {e}")
        db.rollback()
    finally:
        db.close()
    
    return checkpoint_path


def train_mccfr(format_type: str = "NL10", total_iterations: int = 250000,
               checkpoint_interval: int = 2000, num_processes: int = 4):
    """
    Обучение MCCFR с multiprocessing
    
    Args:
        format_type: Формат игры (NL10, NL50)
        total_iterations: Общее количество итераций
        checkpoint_interval: Интервал сохранения чекпоинтов
        num_processes: Количество процессов
    """
    print(f"Начало обучения MCCFR для {format_type}")
    print(f"Всего итераций: {total_iterations}")
    print(f"Чекпоинты каждые: {checkpoint_interval} итераций")
    print(f"Процессов: {num_processes}")
    
    # Создаем директорию для чекпоинтов
    checkpoint_dir = Path("checkpoints") / format_type
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Инициализация БД
    init_db()
    
    # Создаем дерево игры
    max_raise_sizes = {
        0: 2,  # PREFLOP: 2 размера
        1: 2,  # FLOP: 2 размера
        2: 3,  # TURN: 3 размера
        3: 3   # RIVER: 3 размера
    }
    
    game_tree = GameTree(max_raise_sizes=max_raise_sizes)
    mccfr = MCCFR(game_tree, num_players=2)
    
    # Обучение с чекпоинтами
    iterations_done = 0
    
    while iterations_done < total_iterations:
        iterations_batch = min(checkpoint_interval, total_iterations - iterations_done)
        
        print(f"\nОбучение: {iterations_done + 1} - {iterations_done + iterations_batch} / {total_iterations}")
        
        # Обучаем батч
        mccfr.train(iterations_batch, verbose=True)
        iterations_done += iterations_batch
        
        # Сохраняем чекпоинт
        checkpoint_path = save_checkpoint(
            mccfr, game_tree, format_type, iterations_done, checkpoint_dir
        )
        print(f"Чекпоинт сохранен: {checkpoint_path}")
        
        # Выводим статистику
        if mccfr.regret_history:
            print(f"Средний regret: {mccfr.regret_history[-1]:.4f}")
        print(f"Узлов в дереве: {len(game_tree.nodes)}")
    
    print(f"\nОбучение завершено!")
    print(f"Всего итераций: {mccfr.iterations}")
    print(f"Узлов в дереве: {len(game_tree.nodes)}")
    
    # Активируем последний чекпоинт
    db = SessionLocal()
    try:
        last_checkpoint = db.query(TrainingCheckpoint).filter(
            TrainingCheckpoint.format == format_type
        ).order_by(TrainingCheckpoint.created_at.desc()).first()
        
        if last_checkpoint:
            # Деактивируем все предыдущие
            db.query(TrainingCheckpoint).filter(
                TrainingCheckpoint.format == format_type
            ).update({'is_active': False})
            
            # Активируем последний
            last_checkpoint.is_active = True
            db.commit()
            print(f"Активирован чекпоинт: {last_checkpoint.checkpoint_id}")
    except Exception as e:
        print(f"Ошибка при активации чекпоинта: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Обучение MCCFR для покерного бота")
    parser.add_argument("--format", type=str, default="NL10", 
                       help="Формат игры (NL10, NL50)")
    parser.add_argument("--iterations", type=int, default=250000,
                       help="Количество итераций обучения")
    parser.add_argument("--checkpoint-interval", type=int, default=2000,
                       help="Интервал сохранения чекпоинтов")
    parser.add_argument("--processes", type=int, default=4,
                       help="Количество процессов (пока не используется)")
    
    args = parser.parse_args()
    
    train_mccfr(
        format_type=args.format,
        total_iterations=args.iterations,
        checkpoint_interval=args.checkpoint_interval,
        num_processes=args.processes
    )


if __name__ == "__main__":
    main()
