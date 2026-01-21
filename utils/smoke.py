"""
Smoke-тест API без Docker.

Ожидается, что API уже запущен (например: `make run`), и доступен по URL.
Проверки:
- GET /api/v1/health
- POST /api/v1/decide (1 запрос)
- POST /api/v1/log_hand (1 запрос) с table_key
"""

from __future__ import annotations

import argparse
import time
from typing import Any, Dict, Optional

import httpx


def _now_hand_id() -> str:
    return f"smoke_{int(time.time() * 1000)}"


def _health(client: httpx.Client) -> None:
    r = client.get("/api/v1/health")
    r.raise_for_status()


def _decide(client: httpx.Client, *, table_key: str, session_id: str, limit_type: str) -> Dict[str, Any]:
    payload = {
        "hand_id": _now_hand_id(),
        "table_id": table_key,
        "limit_type": limit_type,
        "session_id": session_id,
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {str(i): 100.0 for i in range(6)},
        "bets": {str(i): 0.0 for i in range(6)},
        "total_bets": {str(i): 0.0 for i in range(6)},
        "active_players": [0, 1, 2, 3, 4, 5],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 0.0,
        "small_blind": 0.5,
        "big_blind": 1.0,
    }
    r = client.post("/api/v1/decide", json=payload)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or "action" not in data:
        raise RuntimeError(f"Unexpected /decide response: {data!r}")
    return data


def _log_hand(
    client: httpx.Client,
    *,
    hand_id: str,
    table_key: str,
    session_id: str,
    limit_type: str,
) -> Dict[str, Any]:
    payload = {
        "hand_id": hand_id,
        "table_id": table_key,  # канонический путь
        "table_key": table_key,  # для совместимости/явности
        "limit_type": limit_type,
        "session_id": session_id,
        "players_count": 6,
        "hero_position": 0,
        "hero_cards": "AsKh",
        "board_cards": "QdJc2s",
        "pot_size": 10.0,
        "rake_amount": 0.0,  # пусть backend посчитает если есть rake model, иначе 0 пройдёт
        "hero_result": 0.0,
        "hand_history": None,
    }
    r = client.post("/api/v1/log_hand", json=payload)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or data.get("status") not in {"logged", "success"}:
        raise RuntimeError(f"Unexpected /log_hand response: {data!r}")
    return data


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test for Poker Rake Bot API (no-docker)")
    parser.add_argument("--api", default="http://localhost:8000", help="Base API url (default: http://localhost:8000)")
    parser.add_argument("--table-key", default="table_1", help="Table key (external_table_id)")
    parser.add_argument("--session-id", default="smoke_session", help="Session id (string)")
    parser.add_argument("--limit", default="NL10", help="Limit type, e.g. NL10")
    parser.add_argument("--api-key", default=None, help="Optional X-API-Key")
    args = parser.parse_args(argv)

    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    with httpx.Client(base_url=args.api, timeout=5.0, headers=headers) as client:
        _health(client)
        decide_resp = _decide(client, table_key=args.table_key, session_id=args.session_id, limit_type=args.limit)

        # Логируем результат руки с тем же hand_id, чтобы связать события.
        hand_id = _now_hand_id()
        log_resp = _log_hand(
            client,
            hand_id=hand_id,
            table_key=args.table_key,
            session_id=args.session_id,
            limit_type=args.limit,
        )

    print("OK")
    print(f"health: ok")
    print(f"decide.action: {decide_resp.get('action')} table_key: {decide_resp.get('table_key')}")
    print(f"log_hand.status: {log_resp.get('status')} table_key: {log_resp.get('table_key')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

