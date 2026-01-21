"""Вычисление статистики бота из раздач"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from data.models import Hand, DecisionLog, BotStats
from data.database import SessionLocal


class BotStatsCalculator:
    """Калькулятор статистики бота"""
    
    def calculate_stats(self, session_id: str, limit_type: str,
                       period_start: datetime, period_end: datetime,
                       db: Session) -> BotStats:
        """
        Вычисляет статистику бота за период
        
        Args:
            session_id: ID сессии
            limit_type: Лимит (NL10, NL50)
            period_start: Начало периода
            period_end: Конец периода
            db: Сессия БД
            
        Returns:
            Объект BotStats
        """
        # Получаем все раздачи за период
        hands = db.query(Hand).filter(
            and_(
                Hand.limit_type == limit_type,
                Hand.timestamp >= period_start,
                Hand.timestamp <= period_end
            )
        ).all()
        
        if not hands:
            # Возвращаем пустую статистику
            return BotStats(
                session_id=session_id,
                limit_type=limit_type,
                period_start=period_start,
                period_end=period_end,
                hands_played=0
            )
        
        # Получаем решения за период
        hand_ids = [hand.hand_id for hand in hands]
        decisions = db.query(DecisionLog).filter(
            DecisionLog.hand_id.in_(hand_ids)
        ).all()
        
        # Вычисляем метрики
        stats = self._calculate_metrics(hands, decisions)
        
        # Создаем или обновляем запись
        bot_stats = db.query(BotStats).filter(
            and_(
                BotStats.session_id == session_id,
                BotStats.limit_type == limit_type,
                BotStats.period_start == period_start
            )
        ).first()
        
        if not bot_stats:
            bot_stats = BotStats(
                session_id=session_id,
                limit_type=limit_type,
                period_start=period_start,
                period_end=period_end
            )
            db.add(bot_stats)
        
        # Обновляем значения
        bot_stats.hands_played = stats["hands_played"]
        bot_stats.vpip = stats["vpip"]
        bot_stats.pfr = stats["pfr"]
        bot_stats.three_bet_pct = stats["three_bet_pct"]
        bot_stats.aggression_factor = stats["aggression_factor"]
        bot_stats.winrate_bb_100 = stats["winrate_bb_100"]
        bot_stats.total_rake = stats["total_rake"]
        bot_stats.rake_per_hour = stats["rake_per_hour"]
        bot_stats.avg_pot_size = stats["avg_pot_size"]
        
        db.commit()
        return bot_stats
    
    def _calculate_metrics(self, hands: List[Hand], decisions: List[DecisionLog]) -> Dict:
        """Вычисляет метрики из раздач и решений"""
        if not hands:
            return {
                "hands_played": 0,
                "vpip": 0.0,
                "pfr": 0.0,
                "three_bet_pct": 0.0,
                "aggression_factor": 0.0,
                "winrate_bb_100": 0.0,
                "total_rake": 0.0,
                "rake_per_hour": 0.0,
                "avg_pot_size": 0.0
            }
        
        hands_played = len(hands)
        
        # VPIP: раздачи где был вход префлоп
        preflop_decisions = [d for d in decisions if d.street == "preflop"]
        vpip_count = sum(1 for d in preflop_decisions 
                        if d.final_action in ["call", "raise", "all_in"])
        vpip = (vpip_count / len(preflop_decisions) * 100) if preflop_decisions else 0.0
        
        # PFR: раздачи с рейзом префлоп
        pfr_count = sum(1 for d in preflop_decisions 
                       if d.final_action in ["raise", "all_in"])
        pfr = (pfr_count / len(preflop_decisions) * 100) if preflop_decisions else 0.0
        
        # 3-bet процент: рейзы в ответ на рейз оппонента префлоп
        # Анализируем решения где был facing_raise и бот сделал raise
        three_bet_opportunities = [d for d in preflop_decisions
                                   if d.meta and d.meta.get("facing_raise", False)]
        three_bet_count = sum(1 for d in three_bet_opportunities
                             if d.final_action in ["raise", "all_in"])
        three_bet_pct = (three_bet_count / len(three_bet_opportunities) * 100) if three_bet_opportunities else 0.0
        
        # Aggression Factor: (bets + raises) / calls
        postflop_decisions = [d for d in decisions if d.street != "preflop"]
        bets_raises = sum(1 for d in postflop_decisions 
                         if d.final_action in ["raise", "bet", "all_in"])
        calls = sum(1 for d in postflop_decisions if d.final_action == "call")
        aggression_factor = bets_raises / calls if calls > 0 else (bets_raises if bets_raises > 0 else 0.0)
        
        # Winrate (bb/100)
        total_result = sum(float(hand.hero_result) for hand in hands)
        big_blind = 1.0  # Упрощенно, нужно брать из конфига
        winrate_bb_100 = (total_result / big_blind) / hands_played * 100 if hands_played > 0 else 0.0
        
        # Rake
        total_rake = sum(float(hand.rake_amount) for hand in hands)

        # Rake per hour - вычисляем из периода раздач
        if len(hands) >= 2:
            # Берём время от первой до последней раздачи
            timestamps = sorted([hand.timestamp for hand in hands if hand.timestamp])
            if timestamps:
                duration = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                hours = max(duration, 0.01)  # Минимум 0.01 часа чтобы избежать деления на 0
            else:
                hours = 1.0
        else:
            hours = 1.0  # Default для одной раздачи

        rake_per_hour = total_rake / hours if hours > 0 else 0.0
        
        # Average pot size
        avg_pot_size = sum(float(hand.pot_size) for hand in hands) / hands_played if hands_played > 0 else 0.0
        
        return {
            "hands_played": hands_played,
            "vpip": vpip,
            "pfr": pfr,
            "three_bet_pct": three_bet_pct,
            "aggression_factor": aggression_factor,
            "winrate_bb_100": winrate_bb_100,
            "total_rake": total_rake,
            "rake_per_hour": rake_per_hour,
            "avg_pot_size": avg_pot_size
        }
    
    def get_current_stats(self, session_id: str, limit_type: str,
                         db: Session) -> Optional[BotStats]:
        """Получает текущую статистику бота"""
        # Статистика за последний час
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(hours=1)
        
        return self.calculate_stats(session_id, limit_type, period_start, period_end, db)


# Глобальный калькулятор
bot_stats_calculator = BotStatsCalculator()
