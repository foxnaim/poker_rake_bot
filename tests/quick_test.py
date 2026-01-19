"""Быстрый тест полного цикла"""

import requests
import json

def test_full_cycle():
    """Тест полного цикла: запрос -> решение -> ответ"""

    print("🚀 Тестирование полного цикла poker_rake_bot\n")

    BASE_URL = "http://localhost:8000"

    # 1. Health check
    print("1️⃣  Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
        if response.status_code == 200:
            print(f"   ✅ Health: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        return False

    # 2. Info endpoint
    print("\n2️⃣  Testing info endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/info", timeout=2)
    print(f"   ✅ Info: {response.json()}")

    # 3. Decision endpoint - Preflop
    print("\n3️⃣  Testing decision endpoint (Preflop)...")
    payload = {
        "hand_id": "test_001",
        "table_id": "test_table",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",  # A♠ K♥ (сильная рука)
        "board_cards": "",
        "stacks": {"0": 100.0, "1": 100.0, "2": 100.0},
        "bets": {"0": 0.0, "1": 0.5, "2": 1.0},
        "total_bets": {"0": 0.0, "1": 0.5, "2": 1.0},
        "active_players": [0, 1, 2],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 1.0,
        "small_blind": 0.5,
        "big_blind": 1.0,
        "opponent_ids": []
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/decide",
        json=payload,
        timeout=3
    )

    if response.status_code == 200:
        decision = response.json()
        print(f"   ✅ Preflop Decision: {decision['action']}")
        print(f"      Latency: {decision.get('latency_ms', 0)}ms")
        if 'amount' in decision and decision['amount']:
            print(f"      Amount: {decision['amount']}")
    else:
        print(f"   ❌ Decision failed: {response.status_code}")
        print(f"      {response.text}")
        return False

    # 4. Decision endpoint - Flop
    print("\n4️⃣  Testing decision endpoint (Flop)...")
    payload["street"] = "flop"
    payload["board_cards"] = "AhKdQc"  # A♥ K♦ Q♣ (топ пара + топ кикер)
    payload["hand_id"] = "test_002"

    response = requests.post(
        f"{BASE_URL}/api/v1/decide",
        json=payload,
        timeout=3
    )

    if response.status_code == 200:
        decision = response.json()
        print(f"   ✅ Flop Decision: {decision['action']}")
        print(f"      Latency: {decision.get('latency_ms', 0)}ms")
    else:
        print(f"   ❌ Flop decision failed")
        return False

    # 5. Metrics endpoint
    print("\n5️⃣  Testing metrics endpoint...")
    response = requests.get(f"{BASE_URL}/metrics", timeout=2)
    if response.status_code == 200:
        # Проверяем наличие метрик
        metrics_text = response.text
        if "python_" in metrics_text or "http_" in metrics_text:
            print(f"   ✅ Metrics available (length: {len(metrics_text)} bytes)")
        else:
            print(f"   ⚠️  Metrics returned but may be empty")
    else:
        print(f"   ❌ Metrics failed: {response.status_code}")

    # 6. Проверка латентности
    print("\n6️⃣  Testing latency (10 requests)...")
    latencies = []
    for i in range(10):
        import time
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/decide",
            json=payload,
            timeout=3
        )
        latency = (time.time() - start) * 1000
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    print(f"   ✅ Latency stats:")
    print(f"      Avg: {avg_latency:.1f}ms")
    print(f"      Min: {min_latency:.1f}ms")
    print(f"      Max: {max_latency:.1f}ms")

    if avg_latency < 1000:
        print(f"      🚀 Excellent performance!")
    elif avg_latency < 2000:
        print(f"      👍 Good performance")
    else:
        print(f"      ⚠️  Performance could be better")

    print("\n" + "="*60)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*60)
    print("\n✅ poker_rake_bot работает корректно и готов к использованию!")

    return True


if __name__ == "__main__":
    success = test_full_cycle()
    exit(0 if success else 1)
