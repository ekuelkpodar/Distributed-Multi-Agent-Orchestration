#!/bin/bash
# Setup script for the Multi-Agent Orchestration Platform

set -e

echo "=========================================="
echo "Multi-Agent Orchestration Platform Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker installed${NC}"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose installed${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is not installed. Please install Python 3.11+${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} installed${NC}"
}

# Setup environment file
setup_environment() {
    echo -e "\n${YELLOW}Setting up environment...${NC}"

    if [ ! -f .env ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file from .env.example${NC}"
        echo -e "${YELLOW}! Please edit .env and add your API keys${NC}"
    else
        echo -e "${GREEN}✓ .env file already exists${NC}"
    fi
}

# Create Python virtual environment
setup_venv() {
    echo -e "\n${YELLOW}Setting up Python virtual environment...${NC}"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✓ Created virtual environment${NC}"
    fi

    source venv/bin/activate

    pip install --upgrade pip
    pip install -r services/orchestrator/requirements.txt
    echo -e "${GREEN}✓ Installed Python dependencies${NC}"
}

# Start infrastructure services
start_infrastructure() {
    echo -e "\n${YELLOW}Starting infrastructure services...${NC}"

    docker-compose up -d postgres redis zookeeper kafka

    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"

    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL..."
    until docker-compose exec -T postgres pg_isready -U agent_user -d agents_db > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo -e " ${GREEN}ready${NC}"

    # Wait for Redis
    echo -n "Waiting for Redis..."
    until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo -e " ${GREEN}ready${NC}"

    # Wait for Kafka
    echo -n "Waiting for Kafka..."
    sleep 10
    echo -e " ${GREEN}ready${NC}"

    echo -e "${GREEN}✓ Infrastructure services started${NC}"
}

# Start application services
start_application() {
    echo -e "\n${YELLOW}Starting application services...${NC}"

    docker-compose up -d orchestrator agent-worker

    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 10

    # Check orchestrator health
    echo -n "Checking orchestrator health..."
    HEALTH_CHECK=$(curl -s http://localhost:8000/api/v1/health/live || echo "failed")
    if [[ "$HEALTH_CHECK" == *"alive"* ]]; then
        echo -e " ${GREEN}healthy${NC}"
    else
        echo -e " ${RED}not responding${NC}"
    fi

    echo -e "${GREEN}✓ Application services started${NC}"
}

# Print service URLs
print_urls() {
    echo -e "\n${GREEN}=========================================="
    echo "Setup Complete!"
    echo "==========================================${NC}"
    echo ""
    echo "Service URLs:"
    echo "  - API:          http://localhost:8000"
    echo "  - API Docs:     http://localhost:8000/docs"
    echo "  - Jaeger UI:    http://localhost:16686"
    echo "  - Grafana:      http://localhost:3000 (admin/admin)"
    echo "  - Redis Insight: http://localhost:8001"
    echo "  - Prometheus:   http://localhost:9090"
    echo ""
    echo "Quick Commands:"
    echo "  - View logs:     docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Run tests:     pytest tests/ -v"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_environment
    # setup_venv  # Uncomment for local development
    start_infrastructure
    start_application
    print_urls
}

main "$@"
