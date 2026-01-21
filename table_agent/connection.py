"""Соединение с backend API"""

import asyncio
import aiohttp
import json
import time
import hashlib
import hmac
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ConnectionConfig:
    """Конфигурация подключения"""
    api_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None  # используется как "флаг" включения HMAC (см. _get_headers)
    timeout: float = 5.0
    retry_count: int = 3
    retry_delay: float = 0.5


class BackendConnection:
    """Управление соединением с backend"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False

    async def connect(self) -> bool:
        """Установить соединение"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )

            # Проверка health
            async with self.session.get(f"{self.config.api_url}/api/v1/health") as resp:
                if resp.status == 200:
                    self._connected = True
                    return True
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    async def disconnect(self):
        """Закрыть соединение"""
        if self.session:
            await self.session.close()
            self.session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.session is not None

    def _get_headers(self, body: str = "", method: str = "GET", path: str = "/") -> Dict[str, str]:
        """Получить заголовки с аутентификацией.

        Важно: backend HMAC сейчас проверяет подпись, вычисленную на основе:
        message = f\"{method}{path}{nonce}{timestamp}{body}\"
        key = X-API-Key
        Поэтому здесь используем api_key как ключ (а api_secret трактуем как флаг 'HMAC enabled').
        """
        headers = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        # HMAC включаем если задан api_secret (как флаг) И есть api_key
        if self.config.api_secret and self.config.api_key:
            timestamp = str(int(time.time()))
            nonce = hashlib.md5(f"{timestamp}{body}".encode()).hexdigest()[:16]

            message = f"{method}{path}{nonce}{timestamp}{body}"
            signature = hmac.new(
                self.config.api_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            headers["X-Timestamp"] = timestamp
            headers["X-Nonce"] = nonce
            headers["X-Signature"] = signature

        return headers

    async def decide(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Получить решение от backend"""
        if not self.is_connected:
            return None

        # Если включен HMAC — backend ожидает сортировку ключей в body (см. api/endpoints/decide.py)
        body = json.dumps(game_state, sort_keys=bool(self.config.api_secret))
        headers = self._get_headers(body, method="POST", path="/api/v1/decide")

        for attempt in range(self.config.retry_count):
            try:
                async with self.session.post(
                    f"{self.config.api_url}/api/v1/decide",
                    data=body,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        error = await resp.text()
                        print(f"API error: {resp.status} - {error}")
            except asyncio.TimeoutError:
                print(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                print(f"Request error: {e}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(self.config.retry_delay)

        return None

    async def log_hand(self, hand_data: Dict[str, Any]) -> bool:
        """Отправить данные о раздаче"""
        if not self.is_connected:
            return False

        body = json.dumps(hand_data)
        headers = self._get_headers(body, method="POST", path="/api/v1/log_hand")

        try:
            async with self.session.post(
                f"{self.config.api_url}/api/v1/log_hand",
                data=body,
                headers=headers
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Log hand error: {e}")
            return False

    async def start_session(self, session_id: str, limit_type: str) -> bool:
        """Начать игровую сессию"""
        if not self.is_connected:
            return False

        body = json.dumps({"session_id": session_id, "limit_type": limit_type})
        headers = self._get_headers(body, method="POST", path="/api/v1/session/start")

        try:
            async with self.session.post(
                f"{self.config.api_url}/api/v1/session/start",
                data=body,
                headers=headers
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Start session error: {e}")
            return False

    async def end_session(self, session_id: str) -> bool:
        """Завершить игровую сессию"""
        if not self.is_connected:
            return False

        body = json.dumps({"session_id": session_id})
        headers = self._get_headers(body, method="POST", path="/api/v1/session/end")

        try:
            async with self.session.post(
                f"{self.config.api_url}/api/v1/session/end",
                data=body,
                headers=headers
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"End session error: {e}")
            return False

    async def heartbeat(self, agent_id: str, session_id: Optional[str], status: str = "online",
                        version: Optional[str] = None, errors: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """HTTP heartbeat (fallback) для agent protocol."""
        if not self.is_connected:
            return None

        payload = {
            "agent_id": agent_id,
            "session_id": session_id,
            "status": status,
            "version": version,
            "errors": errors,
        }
        body = json.dumps(payload)
        headers = self._get_headers(body, method="POST", path="/api/v1/agent/heartbeat")

        try:
            async with self.session.post(
                f"{self.config.api_url}/api/v1/agent/heartbeat",
                data=body,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"Heartbeat error: {e}")
            return None
