#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"

# Verificar argumento
if [ -z "$1" ]; then
    echo -e "${RED}Erro: Informe o arquivo de backup${NC}"
    echo "Uso: ./restore.sh <arquivo_backup.tar.gz>"
    echo ""
    echo "Backups disponiveis:"
    ls -1t "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  Nenhum backup encontrado"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    # Tentar no diretorio de backups
    BACKUP_FILE="$BACKUP_DIR/$(basename "$1")"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Erro: Arquivo nao encontrado: $1${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Alakoro FiberSense - Restore${NC}"
echo "========================================"
echo "Arquivo: $(basename "$BACKUP_FILE")"
echo "Tamanho: $(du -h "$BACKUP_FILE" | cut -f1)"

# Confirmar
read -p "Deseja continuar? Os dados atuais serao sobrescritos! [s/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Restore cancelado${NC}"
    exit 0
fi

# Extrair
TEMP_DIR=$(mktemp -d)
echo -e "\n${YELLOW}Extraindo backup...${NC}"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

BACKUP_NAME=$(ls "$TEMP_DIR" | head -1)
EXTRACTED="$TEMP_DIR/$BACKUP_NAME"

# Restaurar dados
echo -e "\n${YELLOW}Restaurando dados...${NC}"

if [ -d "$EXTRACTED/uploads" ]; then
    rm -rf "$PROJECT_DIR/data/uploads"
    cp -r "$EXTRACTED/uploads" "$PROJECT_DIR/data/"
    echo -e "${GREEN}✓ Uploads restaurados${NC}"
fi

if [ -d "$EXTRACTED/exports" ]; then
    rm -rf "$PROJECT_DIR/data/exports"
    cp -r "$EXTRACTED/exports" "$PROJECT_DIR/data/"
    echo -e "${GREEN}✓ Exports restaurados${NC}"
fi

if [ -f "$EXTRACTED/.env" ]; then
    cp "$EXTRACTED/.env" "$PROJECT_DIR/"
    echo -e "${GREEN}✓ .env restaurado${NC}"
fi

if [ -f "$EXTRACTED/docker-compose.yml" ]; then
    cp "$EXTRACTED/docker-compose.yml" "$PROJECT_DIR/"
    echo -e "${GREEN}✓ docker-compose.yml restaurado${NC}"
fi

# Restaurar Redis
if [ -f "$EXTRACTED/redis_dump.rdb" ]; then
    echo -e "\n${YELLOW}Restaurando Redis...${NC}"
    if docker ps --format '{{.Names}}' | grep -q "redis"; then
        docker cp "$EXTRACTED/redis_dump.rdb" redis:/data/dump.rdb
        docker exec redis redis-cli DEBUG RELOAD > /dev/null 2>&1 || true
        echo -e "${GREEN}✓ Redis restaurado${NC}"
    else
        echo -e "${YELLOW}! Redis nao esta rodando, copiando dump para data/redis/${NC}"
        mkdir -p "$PROJECT_DIR/data/redis"
        cp "$EXTRACTED/redis_dump.rdb" "$PROJECT_DIR/data/redis/"
    fi
fi

# Limpar
rm -rf "$TEMP_DIR"

echo -e "\n========================================"
echo -e "${GREEN}Restore concluido!${NC}"
echo "Reinicie os servicos para aplicar as mudancas:"
echo "  docker-compose restart"
echo "========================================"
