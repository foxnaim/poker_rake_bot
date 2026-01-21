"""Redis кэш для стратегий и профилей"""

import json
import os
import redis
from redis.connection import ConnectionPool
from typing import Dict, Optional, Any
from datetime import timedelta

# Опциональный импорт msgpack
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None


class RedisCache:
    """Кэш для стратегий, профилей и частых спотов"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Args:
            redis_url: URL Redis (если None, берется из переменных окружения)
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Connection pooling для лучшей производительности
        #
        # Важно: если используем msgpack, в Redis кладём bytes. Поэтому
        # decode_responses должен быть False, иначе redis-py попытается
        # декодировать бинарь как UTF-8 и упадёт.
        self.pool = ConnectionPool.from_url(
            redis_url,
            max_connections=50,
            decode_responses=False
        )
        self.redis_client = redis.Redis(connection_pool=self.pool)
        self.default_ttl = 3600  # 1 час по умолчанию
        self.use_msgpack = MSGPACK_AVAILABLE  # Использовать msgpack если доступен
    
    def get_strategy(self, infoset: str, limit_type: str) -> Optional[Dict[str, float]]:
        """
        Получает стратегию из кэша
        
        Args:
            infoset: Информационное множество
            limit_type: Лимит (NL10, NL50)
            
        Returns:
            Стратегия или None
        """
        key = f"strategy:{limit_type}:{infoset}"
        cached = self.redis_client.get(key)
        
        if cached:
            if self.use_msgpack and MSGPACK_AVAILABLE:
                return msgpack.unpackb(cached, raw=False)
            return json.loads(cached.decode("utf-8"))
        return None
    
    def set_strategy(self, infoset: str, limit_type: str, strategy: Dict[str, float],
                    ttl: Optional[int] = None):
        """
        Сохраняет стратегию в кэш
        
        Args:
            infoset: Информационное множество
            limit_type: Лимит
            strategy: Стратегия
            ttl: Время жизни в секундах (если None, используется default_ttl)
        """
        key = f"strategy:{limit_type}:{infoset}"
        if self.use_msgpack and MSGPACK_AVAILABLE:
            value = msgpack.packb(strategy, use_bin_type=True)
        else:
            value = json.dumps(strategy).encode("utf-8")
        
        if ttl is None:
            ttl = self.default_ttl
        
        self.redis_client.setex(key, ttl, value)
    
    def get_opponent_profile(self, opponent_id: str) -> Optional[Dict]:
        """
        Получает профиль оппонента из кэша
        
        Args:
            opponent_id: ID оппонента
            
        Returns:
            Профиль или None
        """
        key = f"opponent:{opponent_id}"
        cached = self.redis_client.get(key)
        
        if cached:
            if self.use_msgpack and MSGPACK_AVAILABLE:
                return msgpack.unpackb(cached, raw=False)
            return json.loads(cached.decode("utf-8"))
        return None
    
    def set_opponent_profile(self, opponent_id: str, profile: Dict, ttl: Optional[int] = None):
        """
        Сохраняет профиль оппонента в кэш
        
        Args:
            opponent_id: ID оппонента
            profile: Профиль
            ttl: Время жизни в секундах
        """
        key = f"opponent:{opponent_id}"
        if self.use_msgpack and MSGPACK_AVAILABLE:
            value = msgpack.packb(profile, use_bin_type=True)
        else:
            value = json.dumps(profile).encode("utf-8")
        
        if ttl is None:
            ttl = self.default_ttl
        
        self.redis_client.setex(key, ttl, value)
    
    def invalidate_opponent_profile(self, opponent_id: str):
        """Инвалидирует профиль оппонента"""
        key = f"opponent:{opponent_id}"
        self.redis_client.delete(key)
    
    def get_game_state_cache(self, state_hash: str) -> Optional[Any]:
        """
        Получает закэшированное состояние игры
        
        Args:
            state_hash: Хэш состояния игры
            
        Returns:
            Закэшированные данные или None
        """
        key = f"gamestate:{state_hash}"
        cached = self.redis_client.get(key)
        
        if cached:
            if self.use_msgpack and MSGPACK_AVAILABLE:
                return msgpack.unpackb(cached, raw=False)
            return json.loads(cached.decode("utf-8"))
        return None
    
    def set_game_state_cache(self, state_hash: str, data: Any, ttl: Optional[int] = None):
        """
        Сохраняет состояние игры в кэш
        
        Args:
            state_hash: Хэш состояния
            data: Данные для кэширования
            ttl: Время жизни в секундах
        """
        key = f"gamestate:{state_hash}"
        if self.use_msgpack and MSGPACK_AVAILABLE:
            value = msgpack.packb(data, use_bin_type=True)
        else:
            value = json.dumps(data).encode("utf-8")
        
        if ttl is None:
            ttl = 300  # 5 минут для состояний игры
        
        self.redis_client.setex(key, ttl, value)
    
    def clear_cache(self, pattern: str = "*"):
        """
        Очищает кэш по паттерну
        
        Args:
            pattern: Паттерн ключей (по умолчанию все)
        """
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)
    
    def ping(self) -> bool:
        """Проверяет соединение с Redis"""
        try:
            return self.redis_client.ping()
        except:
            return False


# Глобальный экземпляр кэша
redis_cache = RedisCache()
