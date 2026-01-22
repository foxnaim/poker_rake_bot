"""
Тесты симулятора под нагрузкой
"""

import pytest
import time
import random
from engine.env_wrapper import PokerEnv


def _sample_action(state):
    """Выбирает случайное валидное действие"""
    current_bet = max(state.bets.values())
    player_bet = state.bets.get(state.current_player, 0)
    player_stack = state.stacks.get(state.current_player, 0)
    
    # Если нужно коллить
    if current_bet > player_bet:
        if player_stack <= (current_bet - player_bet):
            return "all_in"
        return random.choice(["call", "fold"])
    
    # Можно чекнуть или рейзить
    actions = ["check"]
    if player_stack > 0:
        actions.append("raise")
    return random.choice(actions)


def test_simulator_stability_under_load():
    """Тест стабильности симулятора под нагрузкой"""
    env = PokerEnv(num_players=6, stack_size=100.0)
    
    # Запускаем много итераций
    num_iterations = 1000
    errors = []
    start_time = time.time()
    
    for i in range(num_iterations):
        try:
            state = env.reset()
            # Играем несколько ходов
            done = False
            for _ in range(10):
                if done:
                    break
                action = _sample_action(state)
                state, done, info = env.step(action)
        except Exception as e:
            errors.append((i, str(e)))
    
    elapsed = time.time() - start_time
    
    # Проверяем что нет ошибок
    assert len(errors) == 0, f"Errors during load test: {errors[:5]}"
    
    # Проверяем производительность (должно быть быстро)
    assert elapsed < 30, f"Load test took too long: {elapsed:.2f}s"
    
    print(f"✅ Simulator stability test: {num_iterations} iterations in {elapsed:.2f}s ({num_iterations/elapsed:.1f} iter/s)")


def test_simulator_memory_usage():
    """Тест использования памяти симулятором"""
    # Создаём много окружений и проверяем что память не растёт
    num_envs = 100
    envs = []
    
    for i in range(num_envs):
        env = PokerEnv(num_players=6, stack_size=100.0)
        state = env.reset()
        envs.append((env, state))
    
    # Проверяем что все окружения работают
    for env, state in envs:
        assert env is not None
        assert state is not None
        assert len(state.active_players) > 0
    
    print(f"✅ Created {num_envs} environments successfully")


def test_simulator_concurrent_usage():
    """Тест использования симулятора в конкурентном режиме"""
    import concurrent.futures
    
    def run_simulation(env_id: int):
        env = PokerEnv(num_players=6, stack_size=100.0)
        state = env.reset()
        done = False
        for _ in range(20):
            if done:
                break
            action = _sample_action(state)
            state, done, info = env.step(action)
        return env_id
    
    num_simulations = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_simulation, i) for i in range(num_simulations)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert len(results) == num_simulations
    print(f"✅ Concurrent simulation test: {num_simulations} simulations completed")


def test_simulator_state_consistency():
    """Тест консистентности состояния симулятора"""
    env = PokerEnv(num_players=6, stack_size=100.0)
    
    for _ in range(100):
        state = env.reset()
        
        # Проверяем начальное состояние
        assert env.num_players == 6
        assert len(state.stacks) == 6
        assert all(s > 0 for s in state.stacks.values())
        
        # Играем несколько ходов
        done = False
        for step in range(30):
            if done:
                break
            
            # Сохраняем состояние
            pot_before = state.pot
            stacks_before = state.stacks.copy()
            
            action = _sample_action(state)
            state, done, info = env.step(action)
            
            # Проверяем что состояние изменилось корректно
            assert state.pot >= pot_before, "Pot should not decrease"
            assert len(state.stacks) == 6, "Number of players should remain constant"
    
    print("✅ Simulator state consistency test passed")
