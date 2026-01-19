"""WebSocket endpoints для real-time обновлений"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
from datetime import datetime

from api.metrics import (
    bot_vpip, bot_pfr, bot_aggression_factor, bot_winrate_bb_100,
    bot_hands_played_total, bot_rake_per_hour, decision_latency_seconds
)


class ConnectionManager:
    """Менеджер WebSocket подключений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Подключает клиента"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Отключает клиента"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        """Отправляет сообщение всем подключенным клиентам"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Отправляет сообщение конкретному клиенту"""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)


# Глобальный менеджер
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint для real-time обновлений
    
    Отправляет:
    - Последние решения
    - Winrate, hands/hr
    - Нагрузки (latency, requests/sec)
    """
    await manager.connect(websocket)
    
    try:
        # Отправляем начальные данные
        await manager.send_personal_message({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to Poker Rake Bot live stream"
        }, websocket)
        
        # Периодически отправляем статистику
        while True:
            # Собираем метрики из Prometheus
            from api.metrics import (
                bot_winrate_bb_100, bot_hands_played_total,
                decision_latency_seconds, http_requests_total,
                get_metric_value
            )
            
            # Получаем значения метрик
            stats = {
                "type": "stats",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "winrate_nl10": get_metric_value(bot_winrate_bb_100, {"limit_type": "NL10", "session_id": "default"}),
                    "winrate_nl50": get_metric_value(bot_winrate_bb_100, {"limit_type": "NL50", "session_id": "default"}),
                    "hands_per_hour": int(get_metric_value(bot_hands_played_total, {"limit_type": "NL10", "session_id": "default"})),
                    "avg_latency_ms": int(get_metric_value(decision_latency_seconds, {"limit_type": "NL10", "street": "preflop"}) * 1000),
                    "requests_per_sec": 0  # TODO: вычислить из http_requests_total (требует дополнительной логики для rate)
                }
            }
            
            await manager.send_personal_message(stats, websocket)
            await asyncio.sleep(5)  # Обновление каждые 5 секунд
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_decision(decision_data: Dict):
    """
    Отправляет решение всем подключенным клиентам
    
    Args:
        decision_data: Данные решения
    """
    message = {
        "type": "decision",
        "timestamp": datetime.utcnow().isoformat(),
        "data": decision_data
    }
    await manager.broadcast(message)


async def broadcast_hand_result(hand_data: Dict):
    """
    Отправляет результат раздачи всем подключенным клиентам
    
    Args:
        hand_data: Данные раздачи
    """
    message = {
        "type": "hand_result",
        "timestamp": datetime.utcnow().isoformat(),
        "data": hand_data
    }
    await manager.broadcast(message)
