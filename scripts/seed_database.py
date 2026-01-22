#!/usr/bin/env python3
"""
Скрипт заполнения базы данных тестовыми данными.

Usage:
    python -m scripts.seed_database
    python -m scripts.seed_database --full  # Больше данных
"""

import sys
import os
import argparse
import random
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import SessionLocal, init_db
from data.models import (
    Room, Bot, BotConfig, Table, BotSession, Hand,
    DecisionLog, OpponentProfile, Agent, RakeModel, APIKey
)


def create_rooms(db):
    """Создать покер-румы"""
    rooms_data = [
        {'room_link': 'https://pokerking.com/table/nl10', 'type': 'cash', 'status': 'active'},
        {'room_link': 'https://pokerstars.com/table/nl10', 'type': 'cash', 'status': 'active'},
        {'room_link': 'https://888poker.com/table/nl10', 'type': 'cash', 'status': 'active'},
    ]

    created = 0
    for rd in rooms_data:
        if not db.query(Room).filter(Room.room_link == rd['room_link']).first():
            room = Room(**rd)
            db.add(room)
            created += 1

    db.commit()
    print(f"Created {created} rooms")
    return db.query(Room).all()


def create_rake_models(db, rooms):
    """Создать модели рейка"""
    created = 0
    for room in rooms:
        for limit in ['NL10', 'NL25', 'NL50']:
            if not db.query(RakeModel).filter(
                RakeModel.room_id == room.id,
                RakeModel.limit_type == limit
            ).first():
                cap = Decimal('3.0') if limit == 'NL10' else Decimal('6.0') if limit == 'NL25' else Decimal('9.0')
                rake_model = RakeModel(
                    room_id=room.id,
                    limit_type=limit,
                    percent=Decimal('5.0'),
                    cap=cap,
                    min_pot=Decimal('0.20')
                )
                db.add(rake_model)
                created += 1

    db.commit()
    print(f"Created {created} rake models")


def create_bots(db):
    """Создать ботов"""
    bots_data = [
        {'alias': 'Bot1', 'active': True},
        {'alias': 'Bot2', 'active': True},
        {'alias': 'Bot3', 'active': False},
    ]

    created = 0
    for bd in bots_data:
        if not db.query(Bot).filter(Bot.alias == bd['alias']).first():
            bot = Bot(alias=bd['alias'], active=bd['active'])
            db.add(bot)
            created += 1

    db.commit()
    print(f"Created {created} bots")
    return db.query(Bot).filter(Bot.active == True).all()


def create_bot_configs(db, bots):
    """Создать конфигурации ботов"""
    created = 0

    for bot in bots:
        if not db.query(BotConfig).filter(BotConfig.bot_id == bot.id).first():
            config = BotConfig(
                bot_id=bot.id,
                name=f'{bot.alias} Config',
                target_vpip=Decimal('22.0'),
                target_pfr=Decimal('18.0'),
                target_af=Decimal('2.5'),
                exploit_weights={'preflop': 0.3, 'flop': 0.4, 'turn': 0.5, 'river': 0.6},
                limit_types=['NL10', 'NL25'],
                is_default=True
            )
            db.add(config)
            created += 1

    db.commit()
    print(f"Created {created} bot configs")
    return db.query(BotConfig).all()


def create_tables(db, rooms):
    """Создать столы"""
    created = 0
    for room in rooms:
        for i in range(3):
            limit = ['NL10', 'NL25', 'NL50'][i % 3]
            ext_id = f"table_{room.id}_{limit}_{i+1}"

            if not db.query(Table).filter(Table.external_table_id == ext_id).first():
                table = Table(
                    room_id=room.id,
                    external_table_id=ext_id,
                    limit_type=limit,
                    max_players=6
                )
                db.add(table)
                created += 1

    db.commit()
    print(f"Created {created} tables")
    return db.query(Table).all()


def create_api_keys(db):
    """Создать API ключи"""
    keys_data = [
        {'name': 'Agent Key 1', 'permissions': ['agent', 'read']},
        {'name': 'Admin Key', 'permissions': ['admin', 'agent', 'read', 'write']},
        {'name': 'Read Only', 'permissions': ['read']},
    ]

    created = 0
    created_keys = []

    for kd in keys_data:
        if not db.query(APIKey).filter(APIKey.name == kd['name']).first():
            key = secrets.token_urlsafe(32)
            api_key = APIKey(
                key=key,
                name=kd['name'],
                permissions=kd['permissions'],
                is_active=True
            )
            db.add(api_key)
            created += 1
            created_keys.append((kd['name'], key))

    db.commit()
    print(f"Created {created} API keys")

    if created_keys:
        print("\nAPI Keys (save these!):")
        for name, key in created_keys:
            print(f"  {name}: {key}")

    return db.query(APIKey).all()


def create_sessions(db, bots, tables, configs, count=10):
    """Создать сессии"""
    created = 0
    now = datetime.utcnow()

    for i in range(count):
        bot = random.choice(bots)
        table = random.choice(tables)
        config = configs[0] if configs else None

        session_id = f"session_{bot.alias}_{i}_{int(now.timestamp())}"

        if db.query(BotSession).filter(BotSession.session_id == session_id).first():
            continue

        start_time = now - timedelta(hours=random.randint(1, 168))
        duration = random.randint(30, 240)
        end_time = start_time + timedelta(minutes=duration)

        hands = random.randint(50, 500)
        profit = Decimal(str(round(random.uniform(-50, 100), 2)))

        session = BotSession(
            session_id=session_id,
            bot_id=bot.id,
            table_id=table.id,
            bot_config_id=config.id if config else None,
            status='ended' if end_time < now else 'active',
            started_at=start_time,
            ended_at=end_time if end_time < now else None,
            hands_played=hands,
            profit=profit,
            rake_paid=abs(profit) * Decimal('0.05'),
            meta={
                'vpip': round(random.uniform(0.18, 0.28), 3),
                'pfr': round(random.uniform(0.15, 0.22), 3)
            }
        )
        db.add(session)
        created += 1

    db.commit()
    print(f"Created {created} sessions")
    return db.query(BotSession).all()


def create_hands(db, sessions, count_per_session=20):
    """Создать раздачи"""
    actions = ['fold', 'check', 'call', 'bet', 'raise', 'all_in']
    streets = ['preflop', 'flop', 'turn', 'river']
    sample_hands = ['AsKs', 'AhKh', 'QsQc', 'JdJh', 'TsTc', 'AcQd', '9s9h', '8d8c', 'AhJh', 'KsQs']

    created = 0

    for session in sessions[:5]:
        for i in range(count_per_session):
            hero_cards = random.choice(sample_hands)
            street = random.choice(streets)

            board = ""
            if street in ['flop', 'turn', 'river']:
                board = "Qd7c2s"
            if street in ['turn', 'river']:
                board += "8h"
            if street == 'river':
                board += "3c"

            action = random.choice(actions)
            pot = Decimal(str(round(random.uniform(1, 20), 2)))
            result = Decimal(str(round(random.uniform(-float(pot), float(pot) * 2), 2))) if random.random() > 0.3 else Decimal('0')

            hand_id = f"hand_{session.id}_{i}"

            if db.query(Hand).filter(Hand.hand_id == hand_id).first():
                continue

            hand = Hand(
                session_id=session.id,
                hand_id=hand_id,
                table_id=str(session.table_id),
                limit_type='NL10',
                hero_cards=hero_cards,
                board_cards=board,
                hero_position=random.randint(0, 5),
                players_count=random.randint(2, 6),
                pot_size=pot,
                rake_amount=pot * Decimal('0.05'),
                hero_result=result,
                hand_history={
                    'street': street,
                    'action': action,
                    'amount': float(pot * Decimal('0.5'))
                }
            )
            db.add(hand)
            created += 1

    db.commit()
    print(f"Created {created} hands")


def create_opponents(db, count=20):
    """Создать профили оппонентов"""
    created = 0
    player_types = ['fish', 'reg', 'nit', 'lag', 'tag', 'unknown']

    for i in range(count):
        opponent_id = f"player_{random.randint(1000, 9999)}"

        if not db.query(OpponentProfile).filter(OpponentProfile.opponent_id == opponent_id).first():
            profile = OpponentProfile(
                opponent_id=opponent_id,
                table_id='table_1',
                limit_type='NL10',
                hands_played=random.randint(10, 1000),
                vpip=Decimal(str(round(random.uniform(10, 50), 2))),
                pfr=Decimal(str(round(random.uniform(8, 35), 2))),
                aggression_factor=Decimal(str(round(random.uniform(0.5, 4.0), 2))),
                three_bet_pct=Decimal(str(round(random.uniform(2, 15), 2))),
                cbet_pct=Decimal(str(round(random.uniform(40, 80), 2))),
                fold_to_cbet_pct=Decimal(str(round(random.uniform(30, 70), 2))),
                classification=random.choice(player_types)
            )
            db.add(profile)
            created += 1

    db.commit()
    print(f"Created {created} opponent profiles")


def create_agents(db, bots):
    """Создать записи агентов"""
    created = 0

    for bot in bots:
        agent_id = f"agent_{bot.alias}_{secrets.token_hex(4)}"

        if not db.query(Agent).filter(Agent.agent_id == agent_id).first():
            agent = Agent(
                agent_id=agent_id,
                status='offline',
                last_seen=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
                version='1.0.0',
                meta={'os': 'linux', 'bot_alias': bot.alias}
            )
            db.add(agent)
            created += 1

    db.commit()
    print(f"Created {created} agents")


def main():
    parser = argparse.ArgumentParser(description="Seed database with test data")
    parser.add_argument("--full", action="store_true", help="Create more test data")
    parser.add_argument("--reset", action="store_true", help="Clear existing data first")

    args = parser.parse_args()

    print("Initializing database...")
    init_db()

    db = SessionLocal()

    try:
        if args.reset:
            print("Clearing existing data...")
            db.query(DecisionLog).delete()
            db.query(Hand).delete()
            db.query(BotSession).delete()
            db.query(Agent).delete()
            db.query(Table).delete()
            db.query(BotConfig).delete()
            db.query(Bot).delete()
            db.query(RakeModel).delete()
            db.query(APIKey).delete()
            db.query(OpponentProfile).delete()
            db.query(Room).delete()
            db.commit()
            print("Data cleared")

        print("\nCreating test data...")

        rooms = create_rooms(db)
        create_rake_models(db, rooms)
        bots = create_bots(db)
        configs = create_bot_configs(db, bots)
        tables = create_tables(db, rooms)
        create_api_keys(db)

        session_count = 50 if args.full else 10
        sessions = create_sessions(db, bots, tables, configs, count=session_count)

        hands_per_session = 50 if args.full else 20
        create_hands(db, sessions, count_per_session=hands_per_session)

        opponent_count = 100 if args.full else 20
        create_opponents(db, count=opponent_count)

        create_agents(db, bots)

        print("\nDatabase seeded successfully!")

        print("\nSummary:")
        print(f"  Rooms: {db.query(Room).count()}")
        print(f"  Bots: {db.query(Bot).count()}")
        print(f"  Tables: {db.query(Table).count()}")
        print(f"  Sessions: {db.query(BotSession).count()}")
        print(f"  Hands: {db.query(Hand).count()}")
        print(f"  Opponents: {db.query(OpponentProfile).count()}")
        print(f"  API Keys: {db.query(APIKey).count()}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
