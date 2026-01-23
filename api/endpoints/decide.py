"""Endpoint для принятия решений"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import time
import json
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from api.schemas import GameStateRequest, DecisionResponse
from api.decision_maker import make_decision
from api.metrics import decision_latency_seconds, decisions_total
from api.websocket import broadcast_decision
from api.auth import optional_api_key
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["decisions"])

# Timeout для принятия решений (ms)
DECIDE_TIMEOUT_MS = int(os.getenv("DECIDE_TIMEOUT_MS", "500"))

# ThreadPool для блокирующих операций
_executor = ThreadPoolExecutor(max_workers=4)

def _resolve_table_key(db: Session, table_id_in: str | None) -> str | None:
    """Пытается привести table_id к Table.external_table_id."""
    if not table_id_in:
        return None
    try:
        from data.models import Table
        table_id_str = str(table_id_in)
        table = None
        try:
            pk = int(table_id_str)
        except (TypeError, ValueError):
            pk = None
        if pk is not None:
            table = db.query(Table).filter(Table.id == pk).first()
        if table is None:
            table = db.query(Table).filter(Table.external_table_id == table_id_str).first()
        return table.external_table_id if table and table.external_table_id else table_id_str
    except Exception:
        return str(table_id_in)


@router.post("/decide", response_model=DecisionResponse)
async def decide_endpoint(
    request: GameStateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    api_key_valid: bool = Depends(optional_api_key),
    # HMAC опционально (если заголовки присутствуют - проверяем)
    x_signature: str = Header(None, alias="X-Signature"),
    x_nonce: str = Header(None, alias="X-Nonce"),
    x_timestamp: int = Header(None, alias="X-Timestamp")
):
    """
    Принимает решение ботом на основе состояния игры
    
    Поддерживает:
    - GTO стратегии (MCCFR)
    - Exploit коррекции (Opponent Profiler)
    - Смешивание стратегий (Decision Router)
    
    Аутентификация:
    - Простой API key (X-API-Key)
    - HMAC-SHA256 (X-API-Key + X-Signature + X-Nonce + X-Timestamp)
    """
    # Проверяем HMAC если заголовки присутствуют
    if x_signature and x_nonce and x_timestamp is not None:
        # Получаем API key из заголовка
        api_key = http_request.headers.get("X-API-Key")
        if api_key:
            # Получаем body из request (Pydantic модель)
            import json
            body_str = json.dumps(request.dict(), sort_keys=True)
            body_bytes = body_str.encode('utf-8')
            
            # Проверяем HMAC
            from api.auth_hmac import hmac_auth
            if not hmac_auth.verify_hmac(
                api_key, x_signature, x_nonce, x_timestamp,
                "POST", "/api/v1/decide", body_bytes
            ):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid HMAC signature"
                )
    
    start_time = time.time()

    try:
        # Нормализуем table_id -> table_key ПОСЛЕ HMAC-проверки,
        # чтобы подпись считалась по оригинальному body, но логирование/кэш были консистентны.
        table_key = _resolve_table_key(db, getattr(request, "table_id", None))
        if table_key:
            try:
                request.table_id = table_key
            except Exception:
                pass

        # Выполняем make_decision с timeout
        loop = asyncio.get_event_loop()
        try:
            decision = await asyncio.wait_for(
                loop.run_in_executor(_executor, make_decision, request),
                timeout=DECIDE_TIMEOUT_MS / 1000.0
            )
        except asyncio.TimeoutError:
            # Timeout - используем fallback
            from api.decision_stub import make_decision_stub
            from api.metrics import decision_errors_total
            decision_errors_total.labels(limit_type=request.limit_type, error_type="Timeout").inc()

            fallback = make_decision_stub(request)
            latency_ms = int((time.time() - start_time) * 1000)

            # Логируем инцидент
            from api.safe_mode import safe_mode
            safe_mode.buffer_decision({
                "hand_id": request.hand_id,
                "table_id": request.table_id,
                "timeout": True,
                "timeout_ms": DECIDE_TIMEOUT_MS,
                "actual_ms": latency_ms
            })

            return DecisionResponse(
                action=fallback.get("action", "check"),
                amount=fallback.get("amount"),
                table_key=table_key,
                reasoning={
                    **(fallback.get("reasoning") or {}),
                    "fallback": True,
                    "timeout": True,
                    "timeout_ms": DECIDE_TIMEOUT_MS,
                },
                latency_ms=latency_ms,
            )
        latency_ms = decision.get("latency_ms", 0)
        
        # Обновляем метрики
        decision_latency_seconds.labels(
            limit_type=request.limit_type,
            street=request.street
        ).observe(latency_ms / 1000.0)
        
        decisions_total.labels(
            limit_type=request.limit_type,
            action=decision["action"]
        ).inc()
        
        # Обновляем p95/p99 метрики
        from api.metrics import decision_p95_latency_seconds, decision_p99_latency_seconds
        decision_p95_latency_seconds.labels(limit_type=request.limit_type).observe(latency_ms / 1000.0)
        decision_p99_latency_seconds.labels(limit_type=request.limit_type).observe(latency_ms / 1000.0)
        
        # Отправляем через WebSocket
        await broadcast_decision({
            "hand_id": request.hand_id,
            "table_key": table_key,
            "action": decision["action"],
            "amount": decision.get("amount"),
            "latency_ms": latency_ms,
            "limit_type": request.limit_type,
            "street": request.street
        })
        
        return DecisionResponse(
            action=decision["action"],
            amount=decision.get("amount"),
            table_key=table_key,
            reasoning=decision.get("reasoning", {}),
            latency_ms=latency_ms or 0
        )
    
    except Exception as e:
        # Обновляем метрики ошибок
        from api.metrics import decision_errors_total
        decision_errors_total.labels(limit_type=request.limit_type, error_type=type(e).__name__).inc()
        # Safe-mode: при ошибках отдаём дефолтное решение (спека/реальная игра так требуют)
        from api.decision_stub import make_decision_stub
        fallback = make_decision_stub(request)
        latency_ms = int((time.time() - start_time) * 1000)
        return DecisionResponse(
            action=fallback.get("action", "check"),
            amount=fallback.get("amount"),
            reasoning={
                **(fallback.get("reasoning") or {}),
                "fallback": True,
                "error_type": type(e).__name__,
            },
            latency_ms=latency_ms,
        )
