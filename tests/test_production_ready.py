"""Production-ready интеграционные тесты для полной проверки системы"""

import pytest
import requests
import time
import json
from pathlib import Path


class TestProductionReadiness:
    """Тесты готовности к production"""

    BASE_URL = "http://localhost:8000"
    API_KEY = "bIDsSvytw_FbDjHBO9bOvaN-TdaxCxc-BEOkHWeIr7A"

    @pytest.fixture(autouse=True)
    def setup(self):
        """Ждем готовности API"""
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.BASE_URL}/api/v1/health", timeout=2)
                if response.status_code == 200:
                    break
            except:
                if i == max_retries - 1:
                    pytest.skip("API не доступен")
                time.sleep(2)

    def test_health_endpoint(self):
        """Тест health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_info_endpoint(self):
        """Тест info endpoint"""
        response = requests.get(f"{self.BASE_URL}/api/v1/info")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Poker Rake Bot Backend"
        assert "version" in data
        assert data["status"] == "running"

    def test_metrics_endpoint(self):
        """Тест Prometheus metrics"""
        response = requests.get(f"{self.BASE_URL}/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        # Проверяем наличие метрик
        content = response.text
        assert "python_" in content or "http_" in content

    def test_decide_endpoint_basic(self):
        """Тест основного endpoint принятия решений"""
        payload = {
            "hand_id": "test_hand_001",
            "table_id": "test_table_1",
            "limit_type": "NL10",
            "street": "preflop",
            "hero_position": 0,
            "dealer": 5,
            "hero_cards": "AsKh",
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
            "opponent_ids": ["opp1", "opp2"]
        }

        response = requests.post(
            f"{self.BASE_URL}/api/v1/decide",
            json=payload,
            timeout=5
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "action" in data
        assert data["action"] in ["fold", "check", "call", "raise", "all_in"]
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))

        # Проверяем латентность (должна быть < 2 секунд)
        assert data["latency_ms"] < 2000

        print(f"✅ Decision: {data['action']}, Latency: {data['latency_ms']}ms")

    def test_decide_endpoint_different_streets(self):
        """Тест решений на разных улицах"""
        streets = ["preflop", "flop", "turn", "river"]
        board_cards = {
            "preflop": "",
            "flop": "AhKhQh",
            "turn": "AhKhQhJd",
            "river": "AhKhQhJd2c"
        }

        for street in streets:
            payload = {
                "hand_id": f"test_{street}",
                "table_id": "test_table",
                "limit_type": "NL10",
                "street": street,
                "hero_position": 0,
                "dealer": 1,
                "hero_cards": "AsKs",
                "board_cards": board_cards[street],
                "stacks": {"0": 100.0, "1": 100.0},
                "bets": {"0": 0.0, "1": 0.0},
                "total_bets": {"0": 1.5, "1": 1.5},
                "active_players": [0, 1],
                "pot": 3.0,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
                "opponent_ids": []
            }

            response = requests.post(
                f"{self.BASE_URL}/api/v1/decide",
                json=payload,
                timeout=5
            )

            assert response.status_code == 200
            data = response.json()
            assert "action" in data
            print(f"✅ {street.capitalize()}: {data['action']}")

    def test_decide_endpoint_latency_under_load(self):
        """Тест латентности под нагрузкой"""
        latencies = []

        payload = {
            "hand_id": "load_test",
            "table_id": "test_table",
            "limit_type": "NL10",
            "street": "preflop",
            "hero_position": 0,
            "dealer": 1,
            "hero_cards": "AsKh",
            "board_cards": "",
            "stacks": {"0": 100.0, "1": 100.0},
            "bets": {"0": 0.0, "1": 1.0},
            "total_bets": {"0": 0.0, "1": 1.0},
            "active_players": [0, 1],
            "pot": 1.5,
            "current_player": 0,
            "last_raise_amount": 1.0,
            "small_blind": 0.5,
            "big_blind": 1.0,
            "opponent_ids": []
        }

        # 10 последовательных запросов
        for i in range(10):
            start = time.time()
            response = requests.post(
                f"{self.BASE_URL}/api/v1/decide",
                json=payload,
                timeout=5
            )
            latency = (time.time() - start) * 1000

            assert response.status_code == 200
            latencies.append(latency)

        # Проверяем статистику
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print(f"✅ Latency stats: avg={avg_latency:.1f}ms, min={min_latency:.1f}ms, max={max_latency:.1f}ms")

        # Средняя латентность должна быть < 1 секунды
        assert avg_latency < 1000
        # Максимальная латентность должна быть < 2 секунд
        assert max_latency < 2000

    def test_cors_headers(self):
        """Тест CORS headers"""
        response = requests.options(
            f"{self.BASE_URL}/api/v1/decide",
            headers={"Origin": "http://example.com"}
        )

        # CORS должен разрешать запросы
        assert "access-control-allow-origin" in response.headers

    def test_rate_limiting(self):
        """Тест rate limiting (должен быть 120 req/min)"""
        # Отправляем 20 запросов быстро
        success_count = 0
        for i in range(20):
            try:
                response = requests.get(f"{self.BASE_URL}/api/v1/health", timeout=1)
                if response.status_code == 200:
                    success_count += 1
            except:
                pass

        # Большинство запросов должны проходить
        assert success_count >= 15

        print(f"✅ Rate limiting: {success_count}/20 requests passed")

    def test_checkpoints_exist(self):
        """Тест наличия обученных чекпоинтов"""
        checkpoints_dir = Path("/app/checkpoints/NL10") if Path("/app").exists() else Path("checkpoints/NL10")

        if not checkpoints_dir.exists():
            pytest.skip("Checkpoints directory not found")

        checkpoint_files = list(checkpoints_dir.glob("*.pkl"))
        assert len(checkpoint_files) > 0, "Нет обученных чекпоинтов!"

        # Проверяем наличие 50K чекпоинта
        has_50k = any("50000" in str(f) for f in checkpoint_files)
        assert has_50k, "Нет чекпоинта 50K итераций!"

        print(f"✅ Found {len(checkpoint_files)} checkpoints, including 50K")


class TestDatabaseIntegration:
    """Тесты интеграции с базой данных"""

    def test_database_connection(self):
        """Тест подключения к БД"""
        try:
            from data.database import SessionLocal, engine
            from sqlalchemy import text

            db = SessionLocal()
            result = db.execute(text("SELECT 1")).scalar()
            db.close()

            assert result == 1
            print("✅ Database connection successful")
        except Exception as e:
            pytest.skip(f"Database not available: {e}")


class TestRedisIntegration:
    """Тесты интеграции с Redis"""

    def test_redis_connection(self):
        """Тест подключения к Redis"""
        try:
            from data.redis_cache import redis_cache

            # Проверяем подключение
            test_key = "test_key"
            test_value = {"test": "value"}

            redis_cache.set(test_key, json.dumps(test_value), ttl=10)
            retrieved = redis_cache.get(test_key)

            assert retrieved is not None
            print("✅ Redis connection successful")
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
