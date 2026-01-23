#!/usr/bin/env python3
"""
Утилита для ротации API ключей

Использование:
    python -m utils.api_key_rotation --key-id 1 --rotate
    python -m utils.api_key_rotation --list-expired
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

# Добавляем путь к проекту
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from data.database import SessionLocal
from data.models_v1_2 import APIKey
import secrets


def rotate_api_key(db: Session, key_id: int) -> dict:
    """Ротирует API ключ (создаёт новый, деактивирует старый)"""
    key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    if not key:
        return {"error": f"API key {key_id} not found"}
    
    # Генерируем новый ключ
    new_api_key = f"pb_{secrets.token_urlsafe(32)}"
    new_api_secret = secrets.token_urlsafe(64)
    
    # Деактивируем старый
    key.is_active = False
    key.meta = key.meta or {}
    key.meta["rotated_at"] = datetime.now(timezone.utc).isoformat()
    key.meta["rotated_to"] = new_api_key
    
    # Создаём новый ключ
    new_key = APIKey(
        api_key=new_api_key,
        api_secret=new_api_secret,
        client_name=f"{key.client_name}_rotated",
        permissions=key.permissions,
        rate_limit_per_minute=key.rate_limit_per_minute,
        is_admin=key.is_admin,
        is_active=True,
        expires_at=key.expires_at
    )
    
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    return {
        "old_key_id": key_id,
        "new_key_id": new_key.key_id,
        "new_api_key": new_api_key,
        "new_api_secret": new_api_secret,
        "message": "Key rotated successfully"
    }


def list_expired_keys(db: Session, days: int = 30) -> list:
    """Список ключей, которые скоро истекают"""
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    expired = db.query(APIKey).filter(
        APIKey.expires_at.isnot(None),
        APIKey.expires_at < cutoff,
        APIKey.is_active == True
    ).all()
    
    return [
        {
            "key_id": k.key_id,
            "client_name": k.client_name,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "days_until_expiry": (k.expires_at - datetime.now(timezone.utc)).days if k.expires_at else None
        }
        for k in expired
    ]


def main():
    parser = argparse.ArgumentParser(description="API Key Rotation Utility")
    parser.add_argument("--key-id", type=int, help="Key ID to rotate")
    parser.add_argument("--rotate", action="store_true", help="Rotate the key")
    parser.add_argument("--list-expired", action="store_true", help="List keys expiring soon")
    parser.add_argument("--days", type=int, default=30, help="Days threshold for expired list")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.rotate and args.key_id:
            result = rotate_api_key(db, args.key_id)
            print(f"Rotation result: {result}")
            if "error" in result:
                sys.exit(1)
        
        elif args.list_expired:
            expired = list_expired_keys(db, args.days)
            if expired:
                print(f"Keys expiring within {args.days} days:")
                for k in expired:
                    print(f"  Key ID {k['key_id']}: {k['client_name']} (expires in {k['days_until_expiry']} days)")
            else:
                print("No keys expiring soon")
        
        else:
            parser.print_help()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
