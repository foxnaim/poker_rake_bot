#!/bin/bash
#
# Deployment script for Poker Rake Bot
# Usage: ./scripts/deploy.sh [dev|prod]
#

set -e

ENVIRONMENT=${1:-dev}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    log_success "Prerequisites OK"
}

# Setup environment
setup_environment() {
    log_info "Setting up environment for: $ENVIRONMENT"

    cd "$PROJECT_DIR"

    # Create .env if not exists
    if [ ! -f .env ]; then
        log_info "Creating .env file..."
        cat > .env << EOF
# Poker Bot Environment Configuration
ENVIRONMENT=$ENVIRONMENT
POSTGRES_PASSWORD=pokerbot_$(openssl rand -hex 8)
SECRET_KEY=$(openssl rand -hex 32)

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
REACT_APP_API_URL=http://localhost:8000

# Grafana (optional)
GF_SECURITY_ADMIN_PASSWORD=admin
EOF
        log_success ".env file created"
    else
        log_info ".env file already exists"
    fi

    # Create required directories
    mkdir -p checkpoints/NL10 checkpoints/NL50
    mkdir -p data logs monitoring config/layouts
    mkdir -p frontend/build

    log_success "Directories created"
}

# Build images
build_images() {
    log_info "Building Docker images..."

    cd "$PROJECT_DIR"

    if [ "$ENVIRONMENT" = "prod" ]; then
        docker compose build --no-cache
    else
        docker compose build
    fi

    log_success "Docker images built"
}

# Initialize database
init_database() {
    log_info "Initializing database..."

    cd "$PROJECT_DIR"

    # Start postgres first
    docker compose up -d postgres
    sleep 5

    # Run migrations
    docker compose run --rm api python -c "
from data.database import init_db
init_db()
print('Database initialized')
"

    log_success "Database initialized"
}

# Create initial data
create_initial_data() {
    log_info "Creating initial data..."

    docker compose run --rm api python -c "
from data.database import SessionLocal
from data.models import Room, Bot, BotConfig, Table, APIKey
import secrets

db = SessionLocal()

# Create rooms
rooms_data = [
    {'name': 'PokerKing', 'url': 'https://pokerking.com', 'rake_percent': 5.0, 'rake_cap': 3.0},
    {'name': 'PokerStars', 'url': 'https://pokerstars.com', 'rake_percent': 4.5, 'rake_cap': 2.5},
    {'name': '888Poker', 'url': 'https://888poker.com', 'rake_percent': 5.0, 'rake_cap': 3.0},
]

for rd in rooms_data:
    if not db.query(Room).filter(Room.name == rd['name']).first():
        room = Room(**rd)
        db.add(room)
        print(f'Created room: {rd[\"name\"]}')

db.commit()

# Get PokerKing room
pk_room = db.query(Room).filter(Room.name == 'PokerKing').first()

# Create bot config
if not db.query(BotConfig).first():
    config = BotConfig(
        name='Default NL10',
        format='NL10',
        settings={
            'vpip_target': 0.22,
            'pfr_target': 0.18,
            'aggression_factor': 2.5,
            'bluff_frequency': 0.35
        },
        is_active=True
    )
    db.add(config)
    db.commit()
    print('Created default bot config')

# Create bot
if not db.query(Bot).filter(Bot.name == 'Bot1').first():
    config = db.query(BotConfig).first()
    bot = Bot(
        name='Bot1',
        config_id=config.id if config else None,
        is_active=True
    )
    db.add(bot)
    db.commit()
    print('Created Bot1')

# Create table
if not db.query(Table).first() and pk_room:
    table = Table(
        room_id=pk_room.id,
        external_table_id='table_nl10_1',
        table_name='NL10 Table 1',
        limit_type='NL10',
        max_players=6,
        is_active=True
    )
    db.add(table)
    db.commit()
    print('Created table')

# Create API key
if not db.query(APIKey).first():
    key = secrets.token_urlsafe(32)
    api_key = APIKey(
        key=key,
        name='Default Agent Key',
        permissions=['agent', 'read'],
        is_active=True
    )
    db.add(api_key)
    db.commit()
    print(f'Created API Key: {key}')
    print('SAVE THIS KEY - it will be needed for Table Agent!')

db.close()
print('Initial data created')
"

    log_success "Initial data created"
}

# Start services
start_services() {
    log_info "Starting services..."

    cd "$PROJECT_DIR"

    if [ "$ENVIRONMENT" = "prod" ]; then
        docker compose up -d
    else
        # Dev mode - don't start trainer by default
        docker compose up -d postgres redis api dashboard
    fi

    log_success "Services started"
}

# Health check
health_check() {
    log_info "Running health checks..."

    # Wait for API
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "API health check failed"
            exit 1
        fi
        sleep 2
    done

    # Check frontend
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "Frontend is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            log_warn "Frontend health check failed (may still be building)"
        fi
        sleep 2
    done
}

# Show status
show_status() {
    echo ""
    echo "=========================================="
    echo "    Poker Rake Bot - Deployment Complete"
    echo "=========================================="
    echo ""
    echo "Services:"
    echo "  - API:       http://localhost:8000"
    echo "  - Frontend:  http://localhost:3000"
    echo "  - Grafana:   http://localhost:3001 (admin/admin)"
    echo "  - Postgres:  localhost:5433"
    echo "  - Redis:     localhost:6379"
    echo ""
    echo "Commands:"
    echo "  View logs:     docker compose logs -f"
    echo "  Stop:          docker compose down"
    echo "  Restart:       docker compose restart"
    echo ""
    echo "Start Table Agent:"
    echo "  python -m table_agent.main --bot Bot1 --limit NL10 --interactive"
    echo ""
    echo "Calibrate buttons:"
    echo "  python -m tools.calibrate_buttons --room pokerking"
    echo ""
}

# Main
main() {
    echo ""
    echo "=========================================="
    echo "    Poker Rake Bot Deployment"
    echo "    Environment: $ENVIRONMENT"
    echo "=========================================="
    echo ""

    check_prerequisites
    setup_environment
    build_images
    init_database
    create_initial_data
    start_services
    health_check
    show_status
}

# Handle commands
case "${1:-}" in
    stop)
        log_info "Stopping services..."
        docker compose down
        log_success "Services stopped"
        ;;
    restart)
        log_info "Restarting services..."
        docker compose restart
        log_success "Services restarted"
        ;;
    logs)
        docker compose logs -f ${2:-}
        ;;
    status)
        docker compose ps
        ;;
    *)
        main
        ;;
esac
