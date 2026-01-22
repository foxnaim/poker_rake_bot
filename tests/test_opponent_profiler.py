"""Тесты для Opponent Profiler"""

import pytest
from brain.opponent_profiler import OpponentProfiler, PlayerType
from data.models import OpponentProfile
from data.database import SessionLocal, init_db


def test_profiler_initialization():
    """Тест инициализации профайлера"""
    profiler = OpponentProfiler()
    assert profiler.min_hands_for_classification == 20
    assert len(profiler.profiles_cache) == 0


def test_classify_fish():
    """Тест классификации фиша"""
    profiler = OpponentProfiler()
    
    profile = OpponentProfile(
        opponent_id="test_fish",
        vpip=45.0,
        pfr=20.0,
        aggression_factor=1.5,
        hands_played=30
    )
    
    classification = profiler._classify_player(profile)
    assert classification == PlayerType.FISH_LOOSE


def test_classify_nit():
    """Тест классификации нита"""
    profiler = OpponentProfiler()
    
    profile = OpponentProfile(
        opponent_id="test_nit",
        vpip=15.0,
        pfr=12.0,
        aggression_factor=2.0,
        hands_played=30
    )
    
    classification = profiler._classify_player(profile)
    assert classification == PlayerType.NIT


def test_classify_tag():
    """Тест классификации TAG"""
    profiler = OpponentProfiler()
    
    profile = OpponentProfile(
        opponent_id="test_tag",
        vpip=22.0,
        pfr=18.0,  # 80% от VPIP
        aggression_factor=2.5,
        hands_played=30
    )
    
    classification = profiler._classify_player(profile)
    assert classification == PlayerType.TAG


def test_classify_calling_station():
    """Тест классификации calling station"""
    profiler = OpponentProfiler()
    
    profile = OpponentProfile(
        opponent_id="test_calling",
        vpip=25.0,
        pfr=10.0,
        aggression_factor=0.8,  # Низкий AF
        hands_played=30
    )
    
    classification = profiler._classify_player(profile)
    assert classification == PlayerType.CALLING_STATION


def test_update_percentage():
    """Тест обновления процентного значения"""
    profiler = OpponentProfiler()
    
    # Начальное значение
    pct = profiler._update_percentage(0.0, 0, True)
    assert pct == 100.0
    
    # Обновление
    pct = profiler._update_percentage(50.0, 10, True)
    assert 50.0 < pct < 60.0  # Должно увеличиться
    
    pct = profiler._update_percentage(50.0, 10, False)
    assert 40.0 < pct < 50.0  # Должно уменьшиться


def test_suggest_exploit_fish():
    """Тест эксплойта против фиша"""
    profiler = OpponentProfiler()
    
    # Создаем профиль фиша
    db = SessionLocal()
    try:
        # Удаляем старый профиль если есть (для идемпотентности теста)
        existing = db.query(OpponentProfile).filter(OpponentProfile.opponent_id == "test_fish_exploit").first()
        if existing:
            db.delete(existing)
            db.commit()
        
        profile = OpponentProfile(
            opponent_id="test_fish_exploit",
            vpip=45.0,
            pfr=20.0,
            hands_played=30,
            classification=PlayerType.FISH_LOOSE
        )
        db.add(profile)
        db.commit()
        
        exploit = profiler.suggest_exploit(
            "test_fish_exploit",
            "flop",
            {},
            db
        )
        
        assert exploit["type"] == "value_heavy"
        assert "bluff_frequency" in exploit["adjustments"]
        assert exploit["adjustments"]["bluff_frequency"] < 0  # Уменьшаем блефы
        
    finally:
        db.rollback()
        db.close()
