"""
Safe Mode - отказоустойчивый режим работы при сбоях DB/Redis

Обеспечивает:
- Circuit breaker для Redis и DB
- Fallback стратегии при недоступности сервисов
- Буферизация событий для последующей записи
- Graceful degradation для критических endpoints
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone
from functools import wraps
from threading import Lock
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Сервис недоступен
    HALF_OPEN = "half_open"  # Пробуем восстановить


class CircuitBreaker:
    """
    Circuit Breaker паттерн для защиты от каскадных сбоев

    Состояния:
    - CLOSED: нормальная работа, запросы проходят
    - OPEN: сервис недоступен, запросы сразу возвращают fallback
    - HALF_OPEN: пробуем восстановить, один запрос проходит
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        """
        Args:
            name: Имя circuit breaker (для логов)
            failure_threshold: Число ошибок до открытия circuit
            recovery_timeout: Время ожидания перед попыткой восстановления (сек)
            half_open_max_calls: Число успешных вызовов для закрытия circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Проверяем не пора ли перейти в HALF_OPEN
                if self._last_failure_time and \
                   time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"CircuitBreaker {self.name}: OPEN -> HALF_OPEN")
            return self._state

    def record_success(self):
        """Записывает успешный вызов"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"CircuitBreaker {self.name}: HALF_OPEN -> CLOSED")
            elif self._state == CircuitState.CLOSED:
                # Сбрасываем счётчик ошибок при успехе
                self._failure_count = 0

    def record_failure(self):
        """Записывает неудачный вызов"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # При ошибке в HALF_OPEN сразу открываем circuit
                self._state = CircuitState.OPEN
                logger.warning(f"CircuitBreaker {self.name}: HALF_OPEN -> OPEN (failure)")
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"CircuitBreaker {self.name}: CLOSED -> OPEN "
                        f"(failures: {self._failure_count})"
                    )

    def is_available(self) -> bool:
        """Проверяет доступен ли сервис для запросов"""
        return self.state != CircuitState.OPEN

    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_failure": datetime.fromtimestamp(
                self._last_failure_time, tz=timezone.utc
            ).isoformat() if self._last_failure_time else None
        }


class EventBuffer:
    """
    Буфер для событий при недоступности БД

    Сохраняет события в памяти и позволяет их записать когда БД восстановится.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = Lock()

    def add(self, event_type: str, data: Dict[str, Any]):
        """Добавляет событие в буфер"""
        with self._lock:
            self._buffer.append({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    def get_all(self) -> List[Dict[str, Any]]:
        """Возвращает все события из буфера"""
        with self._lock:
            events = list(self._buffer)
            return events

    def clear(self):
        """Очищает буфер"""
        with self._lock:
            self._buffer.clear()

    def size(self) -> int:
        """Возвращает размер буфера"""
        with self._lock:
            return len(self._buffer)


class SafeMode:
    """
    Централизованный Safe Mode для всего приложения

    Управляет circuit breakers для DB и Redis,
    буферизует события при сбоях.
    """

    def __init__(self):
        # Circuit breakers
        self.db_circuit = CircuitBreaker(
            "database",
            failure_threshold=3,
            recovery_timeout=15
        )
        self.redis_circuit = CircuitBreaker(
            "redis",
            failure_threshold=5,
            recovery_timeout=10
        )

        # Буферы событий
        self.decision_buffer = EventBuffer(max_size=5000)
        self.audit_buffer = EventBuffer(max_size=2000)
        self.hand_buffer = EventBuffer(max_size=1000)

        # Флаг safe mode
        self._safe_mode_enabled = os.getenv("SAFE_MODE_ENABLED", "1") == "1"

        # Метрики
        self._fallback_count = 0
        self._buffer_flushes = 0

    @property
    def is_enabled(self) -> bool:
        return self._safe_mode_enabled

    def is_db_available(self) -> bool:
        """Проверяет доступность БД"""
        return self.db_circuit.is_available()

    def is_redis_available(self) -> bool:
        """Проверяет доступность Redis"""
        return self.redis_circuit.is_available()

    def record_db_success(self):
        """Записывает успешный запрос к БД"""
        self.db_circuit.record_success()

    def record_db_failure(self):
        """Записывает неудачный запрос к БД"""
        self.db_circuit.record_failure()

    def record_redis_success(self):
        """Записывает успешный запрос к Redis"""
        self.redis_circuit.record_success()

    def record_redis_failure(self):
        """Записывает неудачный запрос к Redis"""
        self.redis_circuit.record_failure()

    def buffer_decision(self, decision_data: Dict[str, Any]):
        """Буферизует решение при недоступности БД"""
        self.decision_buffer.add("decision", decision_data)

    def buffer_hand(self, hand_data: Dict[str, Any]):
        """Буферизует данные руки при недоступности БД"""
        self.hand_buffer.add("hand", hand_data)

    def buffer_audit(self, audit_data: Dict[str, Any]):
        """Буферизует аудит-событие при недоступности БД"""
        self.audit_buffer.add("audit", audit_data)

    def get_status(self) -> Dict[str, Any]:
        """Возвращает полный статус Safe Mode"""
        return {
            "enabled": self._safe_mode_enabled,
            "db_circuit": self.db_circuit.get_status(),
            "redis_circuit": self.redis_circuit.get_status(),
            "buffers": {
                "decisions": self.decision_buffer.size(),
                "hands": self.hand_buffer.size(),
                "audit": self.audit_buffer.size()
            },
            "metrics": {
                "fallback_count": self._fallback_count,
                "buffer_flushes": self._buffer_flushes
            }
        }

    def increment_fallback(self):
        """Увеличивает счётчик fallback вызовов"""
        self._fallback_count += 1


# Глобальный экземпляр Safe Mode
safe_mode = SafeMode()


def with_db_fallback(fallback_value: Any = None):
    """
    Декоратор для функций с fallback при сбое БД

    Args:
        fallback_value: Значение возвращаемое при сбое

    Usage:
        @with_db_fallback(fallback_value=[])
        def get_profiles(db):
            return db.query(Profile).all()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not safe_mode.is_enabled:
                return func(*args, **kwargs)

            if not safe_mode.is_db_available():
                logger.warning(f"DB unavailable, returning fallback for {func.__name__}")
                safe_mode.increment_fallback()
                return fallback_value

            try:
                result = func(*args, **kwargs)
                safe_mode.record_db_success()
                return result
            except Exception as e:
                safe_mode.record_db_failure()
                logger.error(f"DB error in {func.__name__}: {e}")
                safe_mode.increment_fallback()
                return fallback_value

        return wrapper
    return decorator


def with_redis_fallback(fallback_value: Any = None):
    """
    Декоратор для функций с fallback при сбое Redis

    Args:
        fallback_value: Значение возвращаемое при сбое
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not safe_mode.is_enabled:
                return func(*args, **kwargs)

            if not safe_mode.is_redis_available():
                logger.warning(f"Redis unavailable, returning fallback for {func.__name__}")
                safe_mode.increment_fallback()
                return fallback_value

            try:
                result = func(*args, **kwargs)
                safe_mode.record_redis_success()
                return result
            except Exception as e:
                safe_mode.record_redis_failure()
                logger.error(f"Redis error in {func.__name__}: {e}")
                safe_mode.increment_fallback()
                return fallback_value

        return wrapper
    return decorator


class SafeRedisCache:
    """
    Обёртка над Redis с Safe Mode

    При недоступности Redis:
    - get операции возвращают None
    - set операции игнорируются
    """

    def __init__(self, redis_cache):
        self._cache = redis_cache

    def get_strategy(self, infoset: str, limit_type: str) -> Optional[Dict[str, float]]:
        """Безопасное получение стратегии из кэша"""
        if not safe_mode.is_redis_available():
            return None

        try:
            result = self._cache.get_strategy(infoset, limit_type)
            safe_mode.record_redis_success()
            return result
        except Exception as e:
            safe_mode.record_redis_failure()
            logger.warning(f"Redis get_strategy failed: {e}")
            return None

    def set_strategy(self, infoset: str, limit_type: str, strategy: Dict[str, float],
                    ttl: Optional[int] = None):
        """Безопасное сохранение стратегии в кэш"""
        if not safe_mode.is_redis_available():
            return

        try:
            self._cache.set_strategy(infoset, limit_type, strategy, ttl)
            safe_mode.record_redis_success()
        except Exception as e:
            safe_mode.record_redis_failure()
            logger.warning(f"Redis set_strategy failed: {e}")

    def get_opponent_profile(self, opponent_id: str) -> Optional[Dict]:
        """Безопасное получение профиля оппонента"""
        if not safe_mode.is_redis_available():
            return None

        try:
            result = self._cache.get_opponent_profile(opponent_id)
            safe_mode.record_redis_success()
            return result
        except Exception as e:
            safe_mode.record_redis_failure()
            logger.warning(f"Redis get_opponent_profile failed: {e}")
            return None

    def set_opponent_profile(self, opponent_id: str, profile: Dict, ttl: Optional[int] = None):
        """Безопасное сохранение профиля оппонента"""
        if not safe_mode.is_redis_available():
            return

        try:
            self._cache.set_opponent_profile(opponent_id, profile, ttl)
            safe_mode.record_redis_success()
        except Exception as e:
            safe_mode.record_redis_failure()
            logger.warning(f"Redis set_opponent_profile failed: {e}")

    def ping(self) -> bool:
        """Проверяет соединение с Redis"""
        try:
            result = self._cache.ping()
            if result:
                safe_mode.record_redis_success()
            else:
                safe_mode.record_redis_failure()
            return result
        except Exception:
            safe_mode.record_redis_failure()
            return False


# Endpoint для проверки статуса Safe Mode
def get_safe_mode_status() -> Dict[str, Any]:
    """Возвращает статус Safe Mode для health check"""
    return safe_mode.get_status()
