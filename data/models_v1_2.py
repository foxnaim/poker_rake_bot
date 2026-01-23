"""
DEPRECATED: Модели перенесены в models.py

Этот файл оставлен для обратной совместимости.
Все модели теперь находятся в data/models.py
"""

# Re-export для обратной совместимости
from data.models import (
    Base,
    APIKey,
    Session,
    PerformanceLog,
    Alert,
)

__all__ = ['Base', 'APIKey', 'Session', 'PerformanceLog', 'Alert']
