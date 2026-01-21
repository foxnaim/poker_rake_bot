"""Валидация MCCFR - проверка сходимости и аномалий"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import pickle

from brain.mccfr import MCCFR
from brain.game_tree import GameTree


def plot_regret_convergence(regret_history: List[float], save_path: Optional[Path] = None):
    """
    Строит график сходимости regret
    
    Args:
        regret_history: История regret значений
        save_path: Путь для сохранения графика
    """
    if not regret_history:
        print("Нет данных для графика")
        return
    
    plt.figure(figsize=(10, 6))
    plt.plot(regret_history, label='Average Regret')
    plt.xlabel('Iteration (x100)')
    plt.ylabel('Average Regret')
    plt.title('MCCFR Regret Convergence')
    plt.legend()
    plt.grid(True)
    
    if save_path:
        plt.savefig(save_path)
        print(f"График сохранен: {save_path}")
    else:
        plt.show()
    
    plt.close()


def check_anomalies(regret_history: List[float], threshold: float = 10.0) -> List[int]:
    """
    Проверяет аномалии в regret (резкие скачки)
    
    Args:
        regret_history: История regret
        threshold: Порог для определения аномалии
        
    Returns:
        Список индексов аномалий
    """
    if len(regret_history) < 2:
        return []
    
    anomalies = []
    for i in range(1, len(regret_history)):
        change = abs(regret_history[i] - regret_history[i-1])
        if change > threshold:
            anomalies.append(i)
    
    return anomalies


def validate_strategy(game_tree: GameTree) -> Dict:
    """
    Валидирует стратегию: проверяет корректность вероятностей
    
    Args:
        game_tree: Дерево игры
        
    Returns:
        Словарь с результатами валидации
    """
    results = {
        'total_nodes': len(game_tree.nodes),
        'nodes_with_strategy': 0,
        'invalid_strategies': 0,
        'zero_strategy_nodes': 0
    }
    
    for infoset, node in game_tree.nodes.items():
        if node.actions:
            strategy = node.get_average_strategy()
            
            # Проверяем, что вероятности суммируются в 1
            total_prob = sum(strategy.values())
            
            if abs(total_prob - 1.0) > 0.01:  # Допуск 1%
                results['invalid_strategies'] += 1
                print(f"Невалидная стратегия в {infoset}: сумма = {total_prob}")
            
            # Проверяем на нулевые стратегии
            if all(prob == 0.0 for prob in strategy.values()):
                results['zero_strategy_nodes'] += 1
            
            results['nodes_with_strategy'] += 1
    
    return results


def compare_with_rule_bot(mccfr: MCCFR, num_hands: int = 1000) -> Dict:
    """
    Сравнивает MCCFR бота с простым rule-ботом
    
    Args:
        mccfr: Обученный MCCFR
        num_hands: Количество раздач для теста
        
    Returns:
        Словарь с результатами сравнения
    """
    # Упрощенное сравнение
    # В реальной реализации нужно сыграть раздачи
    
    results = {
        'mccfr_winrate': 0.0,
        'rule_bot_winrate': 0.0,
        'improvement': 0.0
    }
    
    # TODO: Реализовать симуляцию раздач
    print("Сравнение с rule-ботом (TODO: реализовать симуляцию)")
    
    return results


def validate_checkpoint(checkpoint_path: Path) -> Dict:
    """
    Валидирует чекпоинт обучения
    
    Args:
        checkpoint_path: Путь к чекпоинту
        
    Returns:
        Словарь с результатами валидации
    """
    if not checkpoint_path.exists():
        return {'error': 'Checkpoint not found'}
    
    try:
        with open(checkpoint_path, 'rb') as f:
            checkpoint_data = pickle.load(f)
        
        game_tree = checkpoint_data.get('game_tree')
        regret_history = checkpoint_data.get('regret_history', [])
        
        results = {
            'checkpoint_path': str(checkpoint_path),
            'iterations': checkpoint_data.get('mccfr_iterations', 0),
            'regret_history_length': len(regret_history),
            'final_regret': regret_history[-1] if regret_history else 0.0,
            'strategy_validation': validate_strategy(game_tree) if game_tree else {},
            'anomalies': check_anomalies(regret_history) if regret_history else []
        }
        
        # Проверяем сходимость
        if len(regret_history) > 10:
            recent_regret = np.mean(regret_history[-10:])
            early_regret = np.mean(regret_history[:10])
            results['convergence'] = {
                'early_avg': early_regret,
                'recent_avg': recent_regret,
                'improvement': early_regret - recent_regret,
                'is_converging': recent_regret < early_regret
            }
        
        return results
        
    except Exception as e:
        return {'error': str(e)}


def main():
    """Основная функция валидации"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Валидация MCCFR чекпоинта")
    parser.add_argument("--checkpoint", type=str, required=True,
                       help="Путь к чекпоинту")
    parser.add_argument("--plot", action="store_true",
                       help="Построить график regret")
    
    args = parser.parse_args()
    
    checkpoint_path = Path(args.checkpoint)
    results = validate_checkpoint(checkpoint_path)
    
    print("\n=== Результаты валидации ===")
    print(f"Чекпоинт: {results.get('checkpoint_path')}")
    print(f"Итераций: {results.get('iterations')}")
    print(f"Финальный regret: {results.get('final_regret', 0.0):.4f}")
    
    if 'strategy_validation' in results:
        sv = results['strategy_validation']
        print(f"\nВалидация стратегии:")
        print(f"  Всего узлов: {sv.get('total_nodes', 0)}")
        print(f"  Узлов со стратегией: {sv.get('nodes_with_strategy', 0)}")
        print(f"  Невалидных стратегий: {sv.get('invalid_strategies', 0)}")
    
    if 'convergence' in results:
        conv = results['convergence']
        print(f"\nСходимость:")
        print(f"  Ранний средний regret: {conv['early_avg']:.4f}")
        print(f"  Поздний средний regret: {conv['recent_avg']:.4f}")
        print(f"  Улучшение: {conv['improvement']:.4f}")
        print(f"  Сходится: {conv['is_converging']}")
    
    if args.plot and 'regret_history' in results:
        plot_path = checkpoint_path.parent / f"{checkpoint_path.stem}_regret.png"
        # Нужно загрузить regret_history из чекпоинта
        with open(checkpoint_path, 'rb') as f:
            checkpoint_data = pickle.load(f)
        regret_history = checkpoint_data.get('regret_history', [])
        plot_regret_convergence(regret_history, plot_path)


if __name__ == "__main__":
    from typing import Optional
    main()
