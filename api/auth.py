"""Аутентификация через API keys"""

import os
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from functools import wraps
from datetime import datetime

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """Аутентификация через API ключи"""
    
    def __init__(self):
        # В production использовать переменные окружения или БД
        self.valid_keys = set()
        self._load_keys()
    
    def _load_keys(self):
        """Загружает валидные API ключи"""
        # Из переменных окружения
        api_key = os.getenv("API_KEY")
        if api_key:
            self.valid_keys.add(api_key)
        
        # Можно добавить загрузку из БД или файла
        # В production рекомендуется использовать БД
    
    def verify_key(self, api_key: Optional[str]) -> bool:
        """
        Проверяет валидность API ключа
        
        Args:
            api_key: API ключ
            
        Returns:
            True если ключ валиден
        """
        if not api_key:
            return False
        
        # Проверяем в БД
        from data.database import SessionLocal
        from data.models_v1_2 import APIKey
        
        db = SessionLocal()
        try:
            key = db.query(APIKey).filter(
                APIKey.api_key == api_key,
                APIKey.is_active == True
            ).first()
            
            if key:
                # Проверяем срок действия
                if key.expires_at and key.expires_at < datetime.utcnow():
                    return False
                
                # Обновляем last_used
                key.last_used = datetime.utcnow()
                db.commit()
                
                return True
        finally:
            db.close()
        
        # Fallback: проверяем в памяти
        if api_key in self.valid_keys:
            return True
        
        # Проверяем переменные окружения
        env_key = os.getenv("API_KEY")
        if env_key and api_key == env_key:
            return True
        
        return False
    
    def add_key(self, api_key: str):
        """Добавляет новый API ключ"""
        self.valid_keys.add(api_key)
    
    def remove_key(self, api_key: str):
        """Удаляет API ключ"""
        self.valid_keys.discard(api_key)


# Глобальный экземпляр
api_key_auth = APIKeyAuth()


def require_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Dependency для проверки API ключа (обязательный)
    
    Args:
        api_key: API ключ из заголовка
        
    Returns:
        API ключ если валиден
        
    Raises:
        HTTPException если ключ невалиден
    """
    if not api_key_auth.verify_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


def require_admin(api_key: Optional[str] = Security(api_key_header)):
    """
    Dependency для проверки admin прав
    
    Args:
        api_key: API ключ из заголовка
        
    Returns:
        API ключ если валиден и имеет admin права
        
    Raises:
        HTTPException если ключ невалиден или нет admin прав
    """
    if not api_key_auth.verify_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    # Проверяем права (в production из БД)
    permissions = api_key_auth.get_permissions(api_key)
    if "admin" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return api_key


# Опциональная аутентификация (для постепенного внедрения)
def optional_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Опциональная проверка API ключа (не выбрасывает исключение)
    
    Args:
        api_key: API ключ из заголовка
        
    Returns:
        True если ключ валиден, False иначе
    """
    return api_key_auth.verify_key(api_key)
