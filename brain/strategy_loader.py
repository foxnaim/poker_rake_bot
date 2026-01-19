"""Загрузка и использование обученных стратегий"""

import pickle
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.orm import Session

from .game_tree import GameTree
from .mccfr import MCCFR
from data.database import SessionLocal
from data.models import TrainingCheckpoint


class StrategyLoader:
    """Загрузчик обученных стратегий"""
    
    def __init__(self):
        self.active_strategies: Dict[str, MCCFR] = {}
        self.game_trees: Dict[str, GameTree] = {}
    
    def load_strategy(self, format_type: str, checkpoint_id: Optional[str] = None) -> Optional[MCCFR]:
        """
        Загружает стратегию из чекпоинта
        
        Args:
            format_type: Формат игры (NL10, NL50)
            checkpoint_id: ID чекпоинта (если None, загружает активный)
            
        Returns:
            MCCFR объект или None
        """
        db = SessionLocal()
        try:
            if checkpoint_id:
                checkpoint = db.query(TrainingCheckpoint).filter(
                    TrainingCheckpoint.checkpoint_id == checkpoint_id
                ).first()
            else:
                # Загружаем активный чекпоинт
                checkpoint = db.query(TrainingCheckpoint).filter(
                    TrainingCheckpoint.format == format_type,
                    TrainingCheckpoint.is_active == True
                ).first()
            
            if not checkpoint or not checkpoint.file_path:
                return None
            
            # Загружаем из файла
            checkpoint_path = Path(checkpoint.file_path)
            if not checkpoint_path.exists():
                print(f"Чекпоинт не найден: {checkpoint_path}")
                return None
            
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # Восстанавливаем объекты
            game_tree = checkpoint_data.get('game_tree')
            if game_tree:
                self.game_trees[format_type] = game_tree
                
                # Создаем MCCFR с загруженным деревом
                mccfr = MCCFR(game_tree, num_players=2)
                mccfr.iterations = checkpoint_data.get('mccfr_iterations', 0)
                mccfr.regret_history = checkpoint_data.get('regret_history', [])
                
                self.active_strategies[format_type] = mccfr
                return mccfr
            
        except Exception as e:
            print(f"Ошибка при загрузке стратегии: {e}")
            return None
        finally:
            db.close()
        
        return None
    
    def get_action_probabilities(self, format_type: str, infoset: str) -> Dict[str, float]:
        """
        Получает вероятности действий для информационного множества
        
        Args:
            format_type: Формат игры
            infoset: Информационное множество
            
        Returns:
            Словарь {действие: вероятность}
        """
        if format_type not in self.active_strategies:
            # Пытаемся загрузить стратегию
            if not self.load_strategy(format_type):
                return {}
        
        mccfr = self.active_strategies[format_type]
        return mccfr.get_strategy(infoset)
    
    def get_best_action(self, format_type: str, infoset: str) -> Optional[str]:
        """
        Получает лучшее действие (с максимальной вероятностью)
        
        Args:
            format_type: Формат игры
            infoset: Информационное множество
            
        Returns:
            Действие или None
        """
        strategy = self.get_action_probabilities(format_type, infoset)
        if not strategy:
            return None
        
        return max(strategy.items(), key=lambda x: x[1])[0]


# Глобальный загрузчик стратегий
strategy_loader = StrategyLoader()
