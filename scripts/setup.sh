#!/bin/bash
set -e

echo "=========================================="
echo "Alakoro FiberSense - Setup"
echo "=========================================="

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Verificar dependencias
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Erro: $1 nao encontrado${NC}"
        echo "Instale $1 e tente novamente"
        exit 1
    fi
    echo -e "${GREEN}✓ $1 encontrado${NC}"
}

echo -e "\n${YELLOW}Verificando dependencias...${NC}"
check_dependency python3
check_dependency pip
check_dependency node
check_dependency npm
check_dependency docker
check_dependency docker-compose
check_dependency cmake
check_dependency g++

# Python version
PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python ${PY_VERSION}${NC}"

# Setup backend
echo -e "\n${YELLOW}Configurando backend...${NC}"
cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "Criando virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Build C++ engine
echo -e "\n${YELLOW}Compilando engine C++...${NC}"
cd "$PROJECT_DIR/backend/engine"
python3 setup_engine.py

echo -e "${GREEN}✓ Engine C++ compilado${NC}"

# Setup frontend
echo -e "\n${YELLOW}Configurando frontend...${NC}"
cd "$PROJECT_DIR/frontend"

echo "Instalando dependencias Node..."
npm install

echo -e "${GREEN}✓ Frontend configurado${NC}"

# Create .env if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "\n${YELLOW}Criando arquivo .env...${NC}"
    cat > "$PROJECT_DIR/.env" << EOF
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
BACKEND_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
EOF
    echo -e "${GREEN}✓ Arquivo .env criado${NC}"
fi

# Create data directories
mkdir -p "$PROJECT_DIR/data/uploads"
mkdir -p "$PROJECT_DIR/data/exports"
mkdir -p "$PROJECT_DIR/data/backups"

echo -e "\n=========================================="
echo -e "${GREEN}Setup concluido com sucesso!${NC}"
echo "=========================================="
echo ""
echo "Para iniciar o sistema:"
echo "  1. Inicie o Redis:     docker run -d -p 6379:6379 --name redis redis:7-alpine"
echo "  2. Inicie o backend:   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  3. Inicie o frontend:  cd frontend && npm run dev"
echo ""
echo "Ou use Docker Compose:  docker-compose up -d"
echo ""
