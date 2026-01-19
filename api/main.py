"""FastAPI приложение"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import time
import random
import asyncio

from data.database import get_db, init_db
from api.schemas import GameStateRequest, DecisionResponse, HandLogRequest, OpponentProfileResponse
from api.decision_maker import make_decision
from api.middleware import RateLimitMiddleware, ErrorHandlingMiddleware, TimingMiddleware
from api.metrics import get_metrics, update_bot_stats_metrics, decision_latency_seconds, decisions_total
from api.auth import optional_api_key
from api.auth_hmac import verify_hmac_signature
from api.websocket import websocket_endpoint, manager
from api.endpoints import decide as decide_router, log_hand as log_hand_router, profiles as profiles_router, api_keys as api_keys_router, stats as stats_router, sessions as sessions_router, training as training_router
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi import WebSocket
import os

app = FastAPI(
    title="Poker Rake Bot API",
    description="Backend API для покерного бота",
    version="1.3.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "syntaxHighlight": {
            "theme": "agate"
        }
    },
    openapi_url="/openapi.json"  # Явно указываем URL для OpenAPI схемы
)

# Middleware (порядок важен!)
app.add_middleware(TimingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)  # 120 запросов в минуту

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    init_db()

    # Регистрируем роутеры
    app.include_router(decide_router.router)
    app.include_router(log_hand_router.router)
    app.include_router(profiles_router.router)
    app.include_router(api_keys_router.router)
    app.include_router(stats_router.router)
    app.include_router(sessions_router.router)
    app.include_router(training_router.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Корневой endpoint с кастомной темой"""
    from pathlib import Path
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    
    # Fallback если файл не найден
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Poker Rake Bot API</title>
        <meta charset="utf-8">
        <style>
            body { 
                margin: 0; 
                padding: 20px; 
                background: #0B0C10; 
                color: #FFFFFF; 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: #1F2833; 
                padding: 40px; 
                border-radius: 8px; 
                border: 1px solid #C5C6C7; 
            }
            h1 { 
                color: #66FCF1; 
                margin-top: 0;
            }
            .subtitle {
                color: #C5C6C7;
                margin-bottom: 30px;
            }
            .status-badge {
                display: inline-block;
                padding: 6px 12px;
                background: #45A29E;
                color: #0B0C10;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                margin-left: 10px;
            }
            .info-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .card {
                background: #0B0C10;
                padding: 20px;
                border-radius: 6px;
                border: 1px solid #C5C6C7;
            }
            .card-title {
                color: #C5C6C7;
                font-size: 14px;
                margin-bottom: 8px;
            }
            .card-value {
                color: #66FCF1;
                font-size: 24px;
                font-weight: bold;
            }
            .card-description {
                color: #C5C6C7;
                font-size: 12px;
                margin-top: 4px;
            }
            .links {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 30px 0;
            }
            .link { 
                display: inline-block; 
                padding: 12px 24px; 
                background: #66FCF1; 
                color: #000000 !important; 
                text-decoration: none; 
                border-radius: 4px; 
                font-weight: 600;
                transition: background 0.2s;
                border: none;
                font-size: 14px;
            }
            .link:hover {
                background: #45A29E;
                color: #000000 !important;
            }
            .link:visited {
                color: #000000 !important;
            }
            .endpoints {
                margin-top: 40px;
            }
            .endpoints h2 {
                color: #66FCF1;
                margin-bottom: 20px;
            }
            .endpoint-item {
                background: #0B0C10;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 4px;
                border-left: 3px solid #66FCF1;
            }
            .endpoint-method {
                display: inline-block;
                padding: 4px 8px;
                background: #45A29E;
                color: #0B0C10;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 10px;
            }
            .endpoint-path {
                color: #66FCF1;
                font-family: monospace;
                font-size: 14px;
            }
            .endpoint-desc {
                color: #C5C6C7;
                font-size: 13px;
                margin-top: 8px;
            }
            p {
                color: #C5C6C7;
                line-height: 1.6;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎰 Poker Rake Bot API<span class="status-badge">RUNNING</span></h1>
            <p class="subtitle">Серверный "мозг" для 6-max NLHE бота</p>
            
            <div class="info-cards">
                <div class="card">
                    <div class="card-title">Версия</div>
                    <div class="card-value">1.2.0</div>
                    <div class="card-description">Backend API</div>
                </div>
                <div class="card">
                    <div class="card-title">Статус</div>
                    <div class="card-value" style="color: #45A29E;">HEALTHY</div>
                    <div class="card-description">Все системы работают</div>
                </div>
                <div class="card">
                    <div class="card-title">API Endpoints</div>
                    <div class="card-value">10+</div>
                    <div class="card-description">Доступные endpoints</div>
                </div>
            </div>
            
            <div class="links">
                <a href="/docs" class="link">📄 Swagger UI</a>
                <a href="/redoc" class="link">📚 ReDoc</a>
                <a href="/api/v1/health" class="link">❤️ Health Check</a>
                <a href="/metrics" class="link">📊 Prometheus Metrics</a>
                <a href="/api/v1/info" class="link">ℹ️ API Info</a>
            </div>
            
            <div class="endpoints">
                <h2>Основные Endpoints</h2>
                <div class="endpoint-item">
                    <span class="endpoint-method">POST</span>
                    <span class="endpoint-path">/api/v1/decide</span>
                    <div class="endpoint-desc">Принятие решения ботом</div>
                </div>
                <div class="endpoint-item">
                    <span class="endpoint-method">POST</span>
                    <span class="endpoint-path">/api/v1/log_hand</span>
                    <div class="endpoint-desc">Логирование раздачи</div>
                </div>
                <div class="endpoint-item">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/v1/opponent/{id}</span>
                    <div class="endpoint-desc">Профиль оппонента</div>
                </div>
                <div class="endpoint-item">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/v1/health</span>
                    <div class="endpoint-desc">Health check</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon endpoint"""
    # Возвращаем пустой ответ с правильным content-type
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


@app.get("/api/v1/info")
async def api_info():
    """Информация об API"""
    return {
        "service": "Poker Rake Bot Backend",
        "version": "1.2.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(get_metrics(), media_type="text/plain")


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений"""
    await websocket_endpoint(websocket)


@app.post("/api/v1/decide", response_model=DecisionResponse)
async def decide(
    request: GameStateRequest,
    db: Session = Depends(get_db),
    api_key_valid: bool = Depends(optional_api_key)
):
    """
    Основной endpoint для принятия решения ботом
    
    Args:
        request: Состояние игры
        
    Returns:
        Решение бота (действие и размер ставки)
    """
    start_time = time.time()
    
    try:
        # Decision Router - GTO + Exploit
        decision = make_decision(request)
        
        # Латентность уже измерена в make_decision
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
        
        return DecisionResponse(
            action=decision["action"],
            amount=decision.get("amount"),
            reasoning=decision.get("reasoning", {}),
            latency_ms=latency_ms or 0
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/log_hand")
async def log_hand(
    request: HandLogRequest,
    db: Session = Depends(get_db)
):
    """
    Логирование завершенной раздачи
    
    Args:
        request: Данные раздачи
    """
    try:
        # В будущем: сохранение в БД
        # save_hand(db, request)
        return {"status": "logged", "hand_id": request.hand_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/opponent/{opponent_id}", response_model=OpponentProfileResponse)
async def get_opponent_profile(
    opponent_id: str,
    db: Session = Depends(get_db)
):
    """
    Получение профиля оппонента
    
    Args:
        opponent_id: ID оппонента
    """
    # Stub - возвращает пустой профиль
    return OpponentProfileResponse(
        opponent_id=opponent_id,
        vpip=0.0,
        pfr=0.0,
        three_bet_pct=0.0,
        aggression_factor=0.0,
        hands_played=0,
        classification="unknown"
    )


# Кастомная OpenAPI схема
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Poker Rake Bot API",
        version="1.3.0",
        description="""
        Backend API для покерного бота.
        
        ## Основные endpoints:
        
        - `POST /api/v1/decide` - Принятие решения ботом
        - `POST /api/v1/log_hand` - Логирование раздачи
        - `GET /api/v1/opponent/{id}` - Профиль оппонента
        - `GET /api/v1/health` - Health check
        - `GET /metrics` - Prometheus метрики
        
        ## Аутентификация:
        
        API ключи передаются через заголовок `X-API-Key` (опционально).
        
        ## Rate Limiting:
        
        По умолчанию: 120 запросов в минуту на IP.
        """,
        routes=app.routes,
    )
    
    # Исправляем версию OpenAPI для совместимости с ReDoc
    if "openapi" in openapi_schema:
        openapi_schema["openapi"] = "3.0.2"
    
    # Добавляем security схемы
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Переопределяем Swagger UI для добавления кастомной темы
from fastapi.openapi.docs import get_swagger_ui_html

# Переопределяем endpoint /docs
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Кастомная Swagger UI с темной темой"""
    # Получаем стандартный HTML
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
    
    # Читаем JavaScript файл темы
    from pathlib import Path
    theme_js_path = Path(__file__).parent / "static" / "swagger_theme.js"
    theme_js = ""
    if theme_js_path.exists():
        with open(theme_js_path, 'r', encoding='utf-8') as f:
            theme_js = f.read()
    
    # Модифицируем HTML, добавляя скрипт темы
    if theme_js:
        # Получаем тело ответа как строку
        html_body_bytes = b""
        if hasattr(html_response, 'body'):
            html_body_bytes = html_response.body
        
        # Декодируем в строку
        html_body = html_body_bytes.decode('utf-8') if isinstance(html_body_bytes, bytes) else str(html_body_bytes)
        
        # Вставляем скрипт перед закрывающим тегом body
        if '</body>' in html_body:
            html_body = html_body.replace('</body>', f'<script>{theme_js}</script></body>')
        elif '</html>' in html_body:
            html_body = html_body.replace('</html>', f'<script>{theme_js}</script></html>')
        else:
            html_body = html_body + f'<script>{theme_js}</script>'
        
        # Создаем новый HTMLResponse с модифицированным контентом
        return HTMLResponse(content=html_body)
    
    return html_response


# Endpoint для статического JavaScript файла (на случай прямого доступа)
@app.get("/static/swagger_theme.js", include_in_schema=False)
async def swagger_ui_theme_js():
    """Кастомная тема для Swagger UI (JavaScript)"""
    from pathlib import Path
    theme_js_path = Path(__file__).parent / "static" / "swagger_theme.js"
    if theme_js_path.exists():
        with open(theme_js_path, 'r', encoding='utf-8') as f:
            return PlainTextResponse(f.read(), media_type="application/javascript")
    return PlainTextResponse("", media_type="application/javascript")


# Переопределяем ReDoc для добавления кастомной темы
from fastapi.openapi.docs import get_redoc_html

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """ReDoc документация API"""
    # Используем стабильную версию ReDoc
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
