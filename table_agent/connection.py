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
    api_secret: Optional[str] = None
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

    def _get_headers(self, body: str = "") -> Dict[str, str]:
        """Получить заголовки с аутентификацией"""
        headers = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        if self.config.api_secret:
            timestamp = str(int(time.time()))
            nonce = hashlib.md5(f"{timestamp}{body}".encode()).hexdigest()[:16]

            message = f"{timestamp}{nonce}{body}"
            signature = hmac.new(
                self.config.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            headers["X-Timestamp"] = timestamp
            headers["X-Nonce"] = nonce
            headers["X-Signature"] = signature

        return headers

    async def decide(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Получить решение от backend"""
        if not self.is_connected:
            return None

        body = json.dumps(game_state)
        headers = self._get_headers(body)

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
        headers = self._get_headers(body)

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
        headers = self._get_headers(body)

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
        headers = self._get_headers(body)

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
