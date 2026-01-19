"""Middleware для API: rate limiting, error handling"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from collections import defaultdict
from typing import Dict


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Получаем IP клиента
        client_ip = request.client.host if request.client else "unknown"
        
        # Проверяем rate limit
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Очищаем старые запросы
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_ago
        ]
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute"
                }
            )
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(current_time)
        
        # Продолжаем обработку
        response = await call_next(request)
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки ошибок"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        
        except HTTPException:
            # Пробрасываем HTTP исключения как есть
            raise
        
        except Exception as e:
            # Логируем ошибку
            import traceback
            print(f"Unhandled error: {e}")
            traceback.print_exc()

            # Возвращаем общую ошибку
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": str(e)
                }
            )


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware для измерения времени ответа"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
