"""Логирование решений в БД"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session

from data.models import DecisionLog
from data.database import SessionLocal


class DecisionLogger:
    """Логгер решений бота"""
    
    def __init__(self):
        self.enabled = True
    
    def log_decision(self, hand_id: str, street: str, game_state: Dict,
                    gto_strategy: Optional[Dict] = None,
                    exploit_adjustments: Optional[Dict] = None,
                    final_action: str = "",
                    action_amount: Optional[float] = None,
                    reasoning: Optional[Dict] = None,
                    latency_ms: Optional[int] = None,
                    session_id: Optional[str] = None,
                    db_session: Optional[Session] = None) -> str:
        """
        Логирует решение в БД
        
        Args:
            hand_id: ID раздачи
            street: Улица
            game_state: Состояние игры
            gto_strategy: GTO стратегия
            exploit_adjustments: Эксплойт-коррекции
            final_action: Финальное действие
            action_amount: Размер ставки
            reasoning: Объяснение решения
            latency_ms: Время ответа в миллисекундах
            db_session: Сессия БД (если None, создается новая)
            
        Returns:
            ID решения
        """
        if not self.enabled:
            return ""
        
        decision_id = f"decision_{uuid.uuid4().hex[:16]}"
        
        should_close = False
        if db_session is None:
            db = SessionLocal()
            should_close = True
        else:
            db = db_session
        
        try:
            # Получаем session_id из строки (если передан)
            session_id_int = None
            if session_id:
                from data.models import BotSession
                # Используем правильную сессию БД
                session_query_db = db if db_session is None else db_session
                session = session_query_db.query(BotSession).filter(BotSession.session_id == session_id).first()
                if session:
                    session_id_int = session.id
            
            decision_log = DecisionLog(
                hand_id=hand_id,
                decision_id=decision_id,
                session_id=session_id_int,
                street=street,
                game_state=game_state,
                gto_action=gto_strategy,
                exploit_action=exploit_adjustments,
                final_action=final_action,
                action_amount=action_amount,
                reasoning=reasoning,
                latency_ms=latency_ms,
                timestamp=datetime.utcnow()
            )
            
            db.add(decision_log)
            db.commit()
            
            return decision_id
        
        except Exception as e:
            db.rollback()
            print(f"Ошибка при логировании решения: {e}")
            return ""
        
        finally:
            if should_close:
                db.close()
    
    def disable(self):
        """Отключает логирование"""
        self.enabled = False
    
    def enable(self):
        """Включает логирование"""
        self.enabled = True


# Глобальный логгер
decision_logger = DecisionLogger()
