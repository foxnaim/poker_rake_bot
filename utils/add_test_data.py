"""Скрипт для добавления тестовых данных в БД"""

from data.database import SessionLocal, init_db
from data.models import Hand, OpponentProfile
from brain.opponent_profiler import opponent_profiler
from datetime import datetime, timedelta
import random

def add_test_data():
    """Добавляет тестовые данные для проверки API"""
    db = SessionLocal()
    
    try:
        # Инициализируем БД если нужно
        init_db()
        
        print("Добавляю тестовые данные...")
        
        # Очищаем старые тестовые данные
        print("  - Очищаю старые тестовые данные...")
        db.query(Hand).filter(Hand.hand_id.like("test_hand_%")).delete()
        db.query(OpponentProfile).filter(OpponentProfile.opponent_id.like("opponent_%")).delete()
        db.commit()
        print("  ✓ Старые данные очищены")
        
        # 1. Добавляем тестовые раздачи
        print("  - Добавляю тестовые раздачи...")
        for i in range(20):
            hand = Hand(
                hand_id=f"test_hand_{i+1}",
                table_id="table_1",
                limit_type=random.choice(["NL10", "NL50"]),
                players_count=6,
                hero_position=random.randint(0, 5),
                hero_cards=random.choice(["AsKh", "QsQd", "AhKd", "9s9h", "AcKc"]),
                board_cards=random.choice(["", "AsKhQd", "AsKhQd2c", "AsKhQd2c3h"]),
                pot_size=round(random.uniform(5.0, 50.0), 2),
                rake_amount=round(random.uniform(0.25, 2.5), 2),
                hero_result=round(random.uniform(-20.0, 30.0), 2),
                hand_history={
                    f"opponent_{j}": {
                        "action": random.choice(["fold", "call", "raise"]),
                        "cards": random.choice(["AsKh", "QsQd", "AhKd"]),
                        "position": j
                    }
                    for j in range(1, 6) if j != i % 6
                },
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 24))
            )
            db.add(hand)
        
        db.commit()
        print(f"  ✓ Добавлено 20 тестовых раздач")
        
        # 2. Добавляем тестовые профили оппонентов
        print("  - Добавляю тестовые профили оппонентов...")
        
        opponent_types = [
            {"vpip": 45.0, "pfr": 35.0, "three_bet": 12.0, "af": 2.5, "type": "fish_loose"},
            {"vpip": 15.0, "pfr": 12.0, "three_bet": 5.0, "af": 1.5, "type": "nit"},
            {"vpip": 22.0, "pfr": 18.0, "three_bet": 8.0, "af": 2.2, "type": "tag"},
            {"vpip": 28.0, "pfr": 24.0, "three_bet": 10.0, "af": 3.0, "type": "lag"},
            {"vpip": 35.0, "pfr": 20.0, "three_bet": 6.0, "af": 1.2, "type": "calling_station"},
        ]
        
        for i, opp_type in enumerate(opponent_types):
            opponent_id = f"opponent_{i+1}"
            
            profile = OpponentProfile(
                opponent_id=opponent_id,
                hands_played=random.randint(50, 500),
                vpip=opp_type["vpip"],
                pfr=opp_type["pfr"],
                three_bet_pct=opp_type["three_bet"],
                aggression_factor=opp_type["af"],
                cbet_pct=random.uniform(60.0, 80.0),
                fold_to_cbet_pct=random.uniform(30.0, 50.0),
                classification=opp_type["type"]
            )
            db.add(profile)
        
        db.commit()
        print(f"  ✓ Добавлено 5 тестовых профилей оппонентов")
        
        # 3. Обновляем профили на основе раздач (пропускаем, т.к. профили уже созданы с данными)
        print("  - Профили созданы с начальными данными")
        print(f"  ✓ Пропускаю обновление (профили уже содержат тестовые данные)")
        
        print("\n✅ Тестовые данные успешно добавлены!")
        print("\nТеперь можно протестировать:")
        print("  - GET /api/v1/opponent/opponent_1")
        print("  - GET /api/v1/opponent/opponent_2")
        print("  - POST /api/v1/decide (с тестовыми данными)")
        print("  - POST /api/v1/log_hand (с тестовыми данными)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_test_data()
