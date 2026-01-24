"""Endpoints для управления агентами (физические экземпляры ботов)"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timezone
import json

from api.schemas import (
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentCommandRequest,
    AgentCommandResponse,
    AgentStatusResponse,
    AgentListResponse
)
from data.database import get_db
from data.models import Agent, BotSession

router = APIRouter(prefix="/api/v1", tags=["agents"])


def _get_heartbeat_lag(last_seen: Optional[datetime]) -> float:
    """Calculate heartbeat lag handling timezone-naive datetimes from SQLite"""
    if not last_seen:
        return 0.0
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_seen).total_seconds()


@router.websocket("/agent/ws/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint для heartbeat агентов
    
    Протокол:
    - Агент подключается и отправляет heartbeat каждые N секунд
    - Сервер может отправлять команды (pause, resume, stop, sit_out)
    """
    await websocket.accept()
    db = next(get_db())
    
    try:
        # Регистрируем или обновляем агента
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            agent = Agent(
                agent_id=agent_id,
                status="online",
                last_seen=datetime.now(timezone.utc),
                version=None
            )
            db.add(agent)
        else:
            agent.status = "online"
            agent.last_seen = datetime.now(timezone.utc)
        
        db.commit()
        
        # Отправляем подтверждение подключения
        await websocket.send_json({
            "type": "connected",
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Основной цикл heartbeat
        while True:
            try:
                # Ждём сообщение от агента (heartbeat или команду)
                data = await websocket.receive_json()
                
                if data.get("type") == "heartbeat":
                    # Обновляем last_seen
                    agent.last_seen = datetime.now(timezone.utc)
                    agent.status = data.get("status", "online")
                    agent.version = data.get("version")
                    
                    # Обновляем assigned_session_id если есть
                    if "session_id" in data:
                        session = db.query(BotSession).filter(
                            BotSession.session_id == data["session_id"]
                        ).first()
                        if session:
                            agent.assigned_session_id = session.id
                    
                    # Сохраняем ошибки если есть
                    if "errors" in data:
                        agent.meta = agent.meta or {}
                        agent.meta["last_errors"] = data["errors"]
                        # Обновляем метрики ошибок
                        from api.metrics import agent_errors_total
                        for error in data["errors"]:
                            agent_errors_total.labels(agent_id=agent_id, error_type="general").inc()
                    
                    db.commit()
                    
                    # Обновляем Prometheus метрики
                    from api.metrics import agent_online, agent_heartbeat_lag_seconds
                    agent_online.labels(agent_id=agent_id).set(1.0 if agent.status == "online" else 0.0)
                    agent_heartbeat_lag_seconds.labels(agent_id=agent_id).set(_get_heartbeat_lag(agent.last_seen))
                    
                    # Получаем pending команды из метаданных агента
                    pending_commands = []
                    if agent.meta and "pending_commands" in agent.meta:
                        pending_commands = agent.meta["pending_commands"]
                        # Очищаем очередь после отправки
                        agent.meta["pending_commands"] = []
                        db.commit()

                    # Отправляем ответ с командами
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "commands": pending_commands
                    })
                
                elif data.get("type") == "command_response":
                    # Агент подтвердил выполнение команды
                    command_id = data.get("command_id")
                    command_status = data.get("status", "completed")
                    command_result = data.get("result")

                    # Сохраняем результат в метаданных агента
                    agent.meta = agent.meta or {}
                    if "command_history" not in agent.meta:
                        agent.meta["command_history"] = []

                    agent.meta["command_history"].append({
                        "command_id": command_id,
                        "status": command_status,
                        "result": command_result,
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    })

                    # Храним только последние 50 команд
                    if len(agent.meta["command_history"]) > 50:
                        agent.meta["command_history"] = agent.meta["command_history"][-50:]

                    db.commit()
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except Exception as e:
        # Логируем ошибку
        print(f"WebSocket error for agent {agent_id}: {e}")
    finally:
        # Помечаем агента как offline
        if agent:
            agent.status = "offline"
            db.commit()
            # Обновляем метрики
            from api.metrics import agent_online
            agent_online.labels(agent_id=agent_id).set(0.0)
        db.close()
        await websocket.close()


@router.post("/agent/heartbeat", response_model=AgentHeartbeatResponse)
async def agent_heartbeat_http(
    request: AgentHeartbeatRequest,
    db: Session = Depends(get_db)
):
    """
    HTTP fallback для heartbeat (если WebSocket недоступен)
    
    Агент отправляет:
    - agent_id
    - session_id (опционально)
    - status
    - version
    - errors (опционально)
    """
    agent = db.query(Agent).filter(Agent.agent_id == request.agent_id).first()

    if not agent:
        agent = Agent(
            agent_id=request.agent_id,
            status=request.status or "online",
            last_seen=datetime.now(timezone.utc),
            version=request.version
        )
        db.add(agent)
    else:
        agent.status = request.status or "online"
        agent.last_seen = datetime.now(timezone.utc)
        agent.version = request.version

    # Обновляем assigned_session_id если есть (для новых и существующих агентов)
    if request.session_id:
        session = db.query(BotSession).filter(
            BotSession.session_id == request.session_id
        ).first()
        if session:
            agent.assigned_session_id = session.id

    # Сохраняем ошибки (для новых и существующих агентов)
    if request.errors:
        agent.meta = agent.meta or {}
        agent.meta["last_errors"] = request.errors
        # Обновляем метрики ошибок
        from api.metrics import agent_errors_total
        for error in request.errors:
            agent_errors_total.labels(agent_id=request.agent_id, error_type="general").inc()

    db.commit()
    db.refresh(agent)
    
    # Обновляем Prometheus метрики
    from api.metrics import agent_online, agent_heartbeat_lag_seconds
    agent_online.labels(agent_id=agent.agent_id).set(1.0 if agent.status == "online" else 0.0)
    # Handle timezone-naive datetimes from SQLite
    lag = 0
    if agent.last_seen:
        last_seen = agent.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        lag = (datetime.now(timezone.utc) - last_seen).total_seconds()
    agent_heartbeat_lag_seconds.labels(agent_id=agent.agent_id).set(lag)
    
    # Получаем команды для агента из очереди в метаданных
    pending_commands = []
    if agent.meta and "pending_commands" in agent.meta:
        pending_commands = agent.meta["pending_commands"]
        # Очищаем очередь после отправки
        agent.meta["pending_commands"] = []
        db.commit()

    return AgentHeartbeatResponse(
        status="ok",
        agent_id=agent.agent_id,
        commands=pending_commands
    )


@router.post("/agent/{agent_id}/command", response_model=AgentCommandResponse)
async def send_agent_command(
    agent_id: str,
    request: AgentCommandRequest,
    db: Session = Depends(get_db)
):
    """
    Отправляет команду агенту
    
    Команды:
    - pause: приостановить игру
    - resume: возобновить игру
    - stop: остановить сессию
    - sit_out: выйти из игры (но остаться за столом)
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Агент {agent_id} не найден"
        )
    
    # Валидация команды
    valid_commands = ["pause", "resume", "stop", "sit_out"]
    if request.command not in valid_commands:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестная команда. Допустимые: {', '.join(valid_commands)}"
        )
    
    # Сохраняем команду в метаданных агента
    # В реальной системе это должна быть очередь команд
    agent.meta = agent.meta or {}
    if "pending_commands" not in agent.meta:
        agent.meta["pending_commands"] = []
    
    command_entry = {
        "command": request.command,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": request.reason
    }
    agent.meta["pending_commands"].append(command_entry)
    
    db.commit()
    
    return AgentCommandResponse(
        status="sent",
        agent_id=agent_id,
        command=request.command,
        message=f"Команда {request.command} отправлена агенту"
    )


@router.get("/agent/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Получает статус агента"""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Агент {agent_id} не найден"
        )
    
    # Вычисляем heartbeat lag (секунды с последнего heartbeat)
    heartbeat_lag = _get_heartbeat_lag(agent.last_seen) if agent.last_seen else None

    assigned_session_key = None
    table_key = None
    if agent.assigned_session is not None:
        assigned_session_key = agent.assigned_session.session_id
        if agent.assigned_session.table is not None:
            table_key = agent.assigned_session.table.external_table_id
    
    return AgentStatusResponse(
        agent_id=agent.agent_id,
        status=agent.status,
        last_seen=agent.last_seen,
        version=agent.version,
        assigned_session_id=agent.assigned_session_id,
        assigned_session_key=assigned_session_key,
        table_key=table_key,
        heartbeat_lag_seconds=heartbeat_lag,
        errors=agent.meta.get("last_errors", []) if agent.meta else []
    )


@router.get("/agents", response_model=List[AgentListResponse])
async def list_agents(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получает список агентов"""
    query = db.query(Agent)
    
    if status:
        query = query.filter(Agent.status == status)
    
    agents = query.order_by(desc(Agent.last_seen)).all()
    
    return [
        AgentListResponse(
            agent_id=a.agent_id,
            status=a.status,
            last_seen=a.last_seen,
            version=a.version,
            assigned_session_id=a.assigned_session_id,
            assigned_session_key=(a.assigned_session.session_id if a.assigned_session is not None else None),
            table_key=(a.assigned_session.table.external_table_id if a.assigned_session is not None and a.assigned_session.table is not None else None),
            heartbeat_lag_seconds=_get_heartbeat_lag(a.last_seen) if a.last_seen else None
        )
        for a in agents
    ]
