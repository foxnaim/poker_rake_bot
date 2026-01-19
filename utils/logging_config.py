"""Конфигурация логирования"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None):
    """
    Настраивает логирование
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу логов (если None, только консоль)
    """
    # Формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очистка существующих handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)
    
    # File handler (если указан)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
    
    # Логирование для внешних библиотек
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)


# Инициализация при импорте
import os
log_file = os.getenv("LOG_FILE")
if log_file:
    setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=Path(log_file))
else:
    setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
