"""Проверка подключения к БД"""

from data.database import SessionLocal
from data.models import OpponentProfile

db = SessionLocal()
try:
    count = db.query(OpponentProfile).count()
    print(f'Total profiles in DB: {count}')
    
    p = db.query(OpponentProfile).filter(
        OpponentProfile.opponent_id == 'opponent_1'
    ).first()
    
    print(f'opponent_1 found: {p is not None}')
    if p:
        print(f'VPIP: {p.vpip}, PFR: {p.pfr}, Classification: {p.classification}')
        print(f'Hands played: {p.hands_played}')
finally:
    db.close()
