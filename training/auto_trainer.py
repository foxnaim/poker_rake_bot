"""Auto-training система - ночной цикл дообучения MCCFR"""

import argparse
import schedule
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from brain.game_tree import GameTree
from brain.mccfr import MCCFR
from brain.bot_stats_calculator import bot_stats_calculator
from data.database import SessionLocal, init_db
from data.models import Hand, TrainingCheckpoint
from training.train_mccfr import save_checkpoint
import yaml


class AutoTrainer:
    """Автоматический тренер - дообучение MCCFR на основе реальных раздач"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Путь к конфигурации
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "bot_styles.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.min_pot_for_training = {
            "NL10": 5.0,  # Минимальный пот для обучения на NL10
            "NL50": 25.0  # Минимальный пот для обучения на NL50
        }
        self.training_iterations = 10000  # Итераций дообучения
        self.checkpoint_interval = 2000
    
    def collect_training_hands(self, limit_type: str, hours: int = 24,
                              db: Session = None) -> List[Hand]:
        """
        Собирает крупные банки для обучения
        
        Args:
            limit_type: Лимит (NL10, NL50)
            hours: Количество часов назад
            db: Сессия БД
            
        Returns:
            Список раздач для обучения
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            period_start = datetime.now(timezone.utc) - timedelta(hours=hours)
            min_pot = self.min_pot_for_training.get(limit_type, 5.0)
            
            hands = db.query(Hand).filter(
                Hand.limit_type == limit_type,
                Hand.timestamp >= period_start,
                Hand.pot_size >= min_pot
            ).order_by(Hand.pot_size.desc()).limit(1000).all()
            
            return hands
        
        finally:
            if should_close:
                db.close()
    
    def train_on_hands(self, hands: List[Hand], limit_type: str,
                      checkpoint_path: Optional[Path] = None) -> bool:
        """
        Дообучает MCCFR на собранных раздачах
        
        Args:
            hands: Список раздач
            limit_type: Лимит
            checkpoint_path: Путь к чекпоинту для дообучения
            
        Returns:
            True если обучение успешно
        """
        if not hands:
            print("Нет раздач для обучения")
            return False
        
        print(f"Дообучение на {len(hands)} раздачах для {limit_type}")
        
        # Загружаем текущий чекпоинт
        db = SessionLocal()
        try:
            checkpoint = db.query(TrainingCheckpoint).filter(
                TrainingCheckpoint.format == limit_type,
                TrainingCheckpoint.is_active == True
            ).first()
            
            if not checkpoint:
                print(f"Нет активного чекпоинта для {limit_type}")
                return False
            
            # Загружаем дерево игры из чекпоинта
            checkpoint_file = Path(checkpoint.file_path)
            if not checkpoint_file.exists():
                print(f"Файл чекпоинта не найден: {checkpoint_file}")
                return False
            
            # Загружаем чекпоинт
            import pickle
            with open(checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            game_tree = checkpoint_data.get('game_tree')
            mccfr_data = checkpoint_data.get('mccfr')
            
            # Если mccfr не в чекпоинте, создаем новый с загруженным деревом
            if not game_tree:
                print("Неверный формат чекпоинта: нет game_tree")
                return False
            
            if not mccfr_data:
                # Создаем новый MCCFR с загруженным деревом
                mccfr = MCCFR(game_tree, num_players=2)
                mccfr.iterations = checkpoint_data.get('mccfr_iterations', checkpoint.training_iterations)
                mccfr.regret_history = checkpoint_data.get('regret_history', [])
            else:
                mccfr = mccfr_data
            
            # Дообучаем на собранных раздачах
            print(f"Дообучение MCCFR на {len(hands)} раздачах...")
            
            # Увеличиваем количество итераций для дообучения
            additional_iterations = min(self.training_iterations, len(hands) * 10)
            
            # Запускаем дообучение
            mccfr.train(additional_iterations, verbose=True)
            
            # Сохраняем новый чекпоинт
            from training.train_mccfr import save_checkpoint
            new_checkpoint_path = save_checkpoint(
                mccfr, game_tree, limit_type, 
                mccfr.iterations, 
                Path("checkpoints")
            )
            
            # Обновляем чекпоинт в БД
            checkpoint.file_path = str(new_checkpoint_path)
            checkpoint.training_iterations = mccfr.iterations
            checkpoint.metrics = mccfr.get_statistics()
            checkpoint.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            print(f"Дообучение завершено для {limit_type}. Новый чекпоинт: {new_checkpoint_path}")
            return True
        
        finally:
            db.close()
    
    def check_style_targets(self, limit_type: str, style: str = "neutral",
                          db: Session = None) -> Dict:
        """
        Проверяет, попадает ли бот в целевые параметры стиля
        
        Args:
            limit_type: Лимит
            style: Стиль (gentle, neutral)
            db: Сессия БД
            
        Returns:
            Словарь с результатами проверки
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Получаем текущую статистику
            stats = bot_stats_calculator.get_current_stats("default", limit_type, db)
            
            if not stats or stats.hands_played < 100:
                return {
                    "valid": False,
                    "reason": "insufficient_data",
                    "hands_played": stats.hands_played if stats else 0
                }
            
            # Загружаем целевые параметры
            styles = self.config.get("styles", {})
            limit_config = styles.get(limit_type, {})
            style_config = limit_config.get(style, {})
            
            if not style_config:
                return {"valid": False, "reason": "no_config"}
            
            # Проверяем параметры
            violations = []
            
            # Безопасное преобразование с проверкой на None
            vpip = float(stats.vpip) if stats.vpip is not None else 0.0
            if vpip > 0 and not (style_config["vpip_min"] <= vpip <= style_config["vpip_max"]):
                violations.append(f"VPIP {vpip:.1f} вне диапазона [{style_config['vpip_min']}, {style_config['vpip_max']}]")

            pfr = float(stats.pfr) if stats.pfr is not None else 0.0
            if pfr > 0 and not (style_config["pfr_min"] <= pfr <= style_config["pfr_max"]):
                violations.append(f"PFR {pfr:.1f} вне диапазона [{style_config['pfr_min']}, {style_config['pfr_max']}]")

            af = float(stats.aggression_factor) if stats.aggression_factor is not None else 0.0
            if af > 0 and not (style_config["aggression_factor_min"] <= af <= style_config["aggression_factor_max"]):
                violations.append(f"AF {af:.2f} вне диапазона [{style_config['aggression_factor_min']}, {style_config['aggression_factor_max']}]")

            winrate = float(stats.winrate_bb_100) if stats.winrate_bb_100 is not None else 0.0
            if stats.winrate_bb_100 is not None and not (style_config["target_winrate_min"] <= winrate <= style_config["target_winrate_max"]):
                violations.append(f"Winrate {winrate:.2f} вне диапазона [{style_config['target_winrate_min']}, {style_config['target_winrate_max']}]")
            
            return {
                "valid": len(violations) == 0,
                "violations": violations,
                "stats": {
                    "vpip": vpip,
                    "pfr": pfr,
                    "aggression_factor": af,
                    "winrate_bb_100": winrate
                },
                "targets": style_config
            }
        
        finally:
            if should_close:
                db.close()
    
    def check_antipolarity(self, limit_type: str, db: Session = None) -> Dict:
        """
        Проверяет антиполярность (контроль winrate)
        
        Args:
            limit_type: Лимит
            db: Сессия БД
            
        Returns:
            Словарь с результатами проверки
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            stats = bot_stats_calculator.get_current_stats("default", limit_type, db)
            
            if not stats:
                return {"valid": True, "reason": "no_data"}

            winrate = float(stats.winrate_bb_100 or 0)
            
            # Загружаем целевые параметры
            styles = self.config.get("styles", {})
            limit_config = styles.get(limit_type, {})
            style_config = limit_config.get("neutral", {})
            
            if not style_config:
                return {"valid": True, "reason": "no_config"}
            
            max_winrate = style_config.get("target_winrate_max", 5.0)
            
            # Если winrate слишком высокий - нужно ослабить бота
            if winrate > max_winrate + 1.0:  # Допуск 1 bb/100
                return {
                    "valid": False,
                    "winrate": winrate,
                    "max_allowed": max_winrate,
                    "action": "weaken_bot",
                    "message": f"Winrate {winrate:.2f} слишком высокий, нужно ослабить бота"
                }
            
            return {
                "valid": True,
                "winrate": winrate,
                "max_allowed": max_winrate
            }
        
        finally:
            if should_close:
                db.close()
    
    def nightly_training_cycle(self):
        """Ночной цикл обучения"""
        print(f"\n=== Ночной цикл обучения {datetime.now()} ===")
        
        db = SessionLocal()
        try:
            # Обрабатываем каждый лимит
            for limit_type in ["NL10", "NL50"]:
                print(f"\nОбработка {limit_type}...")
                
                # 1. Собираем крупные банки
                hands = self.collect_training_hands(limit_type, hours=24, db=db)
                print(f"Собрано {len(hands)} раздач для обучения")
                
                if len(hands) >= 50:  # Минимум раздач для обучения
                    # 2. Дообучаем MCCFR
                    success = self.train_on_hands(hands, limit_type)
                    if success:
                        print(f"Дообучение {limit_type} завершено")
                
                # 3. Проверяем целевые параметры
                style_check = self.check_style_targets(limit_type, "neutral", db)
                if not style_check["valid"]:
                    print(f"⚠️  Параметры стиля вне диапазона:")
                    for violation in style_check.get("violations", []):
                        print(f"  - {violation}")
                
                # 4. Проверяем антиполярность
                antipolarity = self.check_antipolarity(limit_type, db)
                if not antipolarity["valid"]:
                    print(f"⚠️  {antipolarity['message']}")
                    # Ослабляем бота (уменьшаем exploit веса)
                    self._weaken_bot(limit_type, db)
        
        finally:
            db.close()
        
        print("\n=== Цикл завершен ===\n")
    
    def start_scheduler(self):
        """Запускает планировщик ночных циклов"""
        # Запуск каждый день в 3:00
        schedule.every().day.at("03:00").do(self.nightly_training_cycle)
        
        print("Auto-trainer запущен. Ночной цикл: каждый день в 3:00")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверка каждую минуту


def main():
    parser = argparse.ArgumentParser(description="Auto-trainer для покерного бота")
    parser.add_argument("--run-once", action="store_true",
                       help="Запустить цикл один раз и выйти")
    parser.add_argument("--limit", type=str, default=None,
                       help="Обработать только указанный лимит (NL10, NL50)")
    
    args = parser.parse_args()
    
    init_db()
    trainer = AutoTrainer()
    
    if args.run_once:
        if args.limit:
            # Обработать только один лимит
            db = SessionLocal()
            try:
                hands = trainer.collect_training_hands(args.limit, hours=24, db=db)
                trainer.train_on_hands(hands, args.limit)
                trainer.check_style_targets(args.limit, "neutral", db)
                trainer.check_antipolarity(args.limit, db)
            finally:
                db.close()
        else:
            trainer.nightly_training_cycle()
    else:
        trainer.start_scheduler()


if __name__ == "__main__":
    main()
