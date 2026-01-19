"""HMAC-SHA256 аутентификация для API"""

import hmac
import hashlib
import time
from typing import Optional, Dict
from fastapi import Security, HTTPException, status, Header, Request
from fastapi.security import APIKeyHeader

from api.auth import APIKeyAuth


class HMACAuth:
    """HMAC-SHA256 аутентификация с nonce и timestamp"""
    
    def __init__(self):
        self.api_key_auth = APIKeyAuth()
        self.nonce_cache: Dict[str, float] = {}  # nonce -> timestamp
        self.nonce_ttl = 300  # 5 минут
    
    def verify_hmac(self, api_key: str, signature: str, nonce: str, 
                   timestamp: int, method: str, path: str, body: bytes) -> bool:
        """
        Проверяет HMAC подпись запроса
        
        Args:
            api_key: API ключ
            signature: HMAC подпись из заголовка
            nonce: Уникальный nonce
            timestamp: Unix timestamp
            method: HTTP метод
            path: Путь запроса
            body: Тело запроса
            
        Returns:
            True если подпись валидна
        """
        # Проверяем API ключ
        if not self.api_key_auth.verify_key(api_key):
            return False
        
        # Проверяем timestamp (не старше 5 минут)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:
            return False
        
        # Проверяем nonce (не должен повторяться)
        if nonce in self.nonce_cache:
            return False
        
        # Вычисляем ожидаемую подпись
        message = f"{method}{path}{nonce}{timestamp}{body.decode('utf-8', errors='ignore')}"
        expected_signature = hmac.new(
            api_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем подписи (constant-time сравнение)
        if not hmac.compare_digest(signature, expected_signature):
            return False
        
        # Сохраняем nonce
        self.nonce_cache[nonce] = current_time
        
        # Очищаем старые nonce
        self._cleanup_nonce_cache()
        
        return True
    
    def _cleanup_nonce_cache(self):
        """Очищает устаревшие nonce"""
        current_time = time.time()
        expired_nonces = [
            nonce for nonce, ts in self.nonce_cache.items()
            if current_time - ts > self.nonce_ttl
        ]
        for nonce in expired_nonces:
            del self.nonce_cache[nonce]
    
    def get_permissions(self, api_key: str) -> list:
        """
        Получает права доступа для API ключа
        
        Args:
            api_key: API ключ
            
        Returns:
            Список прав: ['decide_only', 'log_only', 'admin']
        """
        # В production хранить в БД
        # Пока упрощенно: все ключи имеют все права
        if self.api_key_auth.verify_key(api_key):
            return ['decide_only', 'log_only', 'admin']
        return []


# Глобальный экземпляр
hmac_auth = HMACAuth()


async def verify_hmac_signature(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce"),
    x_timestamp: Optional[int] = Header(None, alias="X-Timestamp")
):
    """
    Dependency для проверки HMAC подписи
    
    Args:
        request: FastAPI Request объект
        x_api_key: API ключ
        x_signature: HMAC подпись
        x_nonce: Уникальный nonce
        x_timestamp: Unix timestamp
        
    Returns:
        API ключ если валиден
        
    Raises:
        HTTPException если подпись невалидна
    """
    # Если HMAC не используется, проверяем только API ключ
    if not x_signature or not x_nonce or x_timestamp is None:
        if not hmac_auth.api_key_auth.verify_key(x_api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key"
            )
        return x_api_key
    
    # Получаем данные из request
    method = request.method
    path = request.url.path
    body = await request.body()
    
    # Проверяем HMAC подпись
    if not hmac_auth.verify_hmac(
        x_api_key or "",
        x_signature,
        x_nonce,
        x_timestamp,
        method,
        path,
        body
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )
    
    return x_api_key
