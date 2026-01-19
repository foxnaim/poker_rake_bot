"""Модели БД для v1.2 (API keys, sessions, performance)"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from data.models import Base


class APIKey(Base):
    """Модель API ключа"""
    __tablename__ = "api_keys"

    key_id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    api_secret = Column(String(255), nullable=False)
    client_name = Column(String(100), nullable=False)
    permissions = Column(ARRAY(Text), default=['decide_only', 'log_only'])
    rate_limit_per_minute = Column(Integer, default=120)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)


class Session(Base):
    """Модель сессии"""
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True)
    client_id = Column(String(100), index=True)
    table_id = Column(String(100), index=True)
    limit_type = Column(String(20))
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    context = Column(JSON)
    is_active = Column(Boolean, default=True, index=True)


class PerformanceLog(Base):
    """Модель лога производительности"""
    __tablename__ = "performance_log"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(100), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    status_code = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    meta_data = Column(JSON)


class Alert(Base):
    """Модель алерта"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    message = Column(Text, nullable=False)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    is_resolved = Column(Boolean, default=False, index=True)
