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
    
    def get_permissions(self, api_key: Optional[str]) -> list:
        """
        Получает список permissions для API ключа
        
        Args:
            api_key: API ключ
            
        Returns:
            Список permissions
        """
        if not api_key:
            return []
        
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
                permissions = list(key.permissions) if key.permissions else []
                
                # Проверяем is_admin (если поле существует)
                if hasattr(key, 'is_admin') and key.is_admin:
                    if 'admin' not in permissions:
                        permissions.append('admin')
                
                return permissions
        finally:
            db.close()
        
        return []
    
    def is_admin(self, api_key: Optional[str]) -> bool:
        """
        Проверяет, является ли ключ admin
        
        Args:
            api_key: API ключ
            
        Returns:
            True если ключ имеет admin права
        """
        permissions = self.get_permissions(api_key)
        return 'admin' in permissions
    
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
    
    # Проверяем права
    if not api_key_auth.is_admin(api_key):
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
