"""Endpoint для принятия решений"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import time
import json

from api.schemas import GameStateRequest, DecisionResponse
from api.decision_maker import make_decision
from api.metrics import decision_latency_seconds, decisions_total
from api.websocket import broadcast_decision
from api.auth import optional_api_key
from data.database import get_db

router = APIRouter(prefix="/api/v1", tags=["decisions"])


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
        decision = make_decision(request)
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
            "action": decision["action"],
            "amount": decision.get("amount"),
            "latency_ms": latency_ms,
            "limit_type": request.limit_type,
            "street": request.street
        })
        
        return DecisionResponse(
            action=decision["action"],
            amount=decision.get("amount"),
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
