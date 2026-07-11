#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="alakoro_backup_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo -e "${YELLOW}Alakoro FiberSense - Backup${NC}"
echo "========================================"

mkdir -p "$BACKUP_PATH"

# Backup de dados
echo -e "\n${YELLOW}Backup de dados...${NC}"
if [ -d "$PROJECT_DIR/data/uploads" ]; then
    cp -r "$PROJECT_DIR/data/uploads" "$BACKUP_PATH/" 2>/dev/null || true
    echo -e "${GREEN}✓ Uploads copiados${NC}"
fi

if [ -d "$PROJECT_DIR/data/exports" ]; then
    cp -r "$PROJECT_DIR/data/exports" "$BACKUP_PATH/" 2>/dev/null || true
    echo -e "${GREEN}✓ Exports copiados${NC}"
fi

# Backup de configuracoes
echo -e "\n${YELLOW}Backup de configuracoes...${NC}"
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_PATH/" 2>/dev/null || true
    echo -e "${GREEN}✓ .env copiado${NC}"
fi

if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_PATH/" 2>/dev/null || true
    echo -e "${GREEN}✓ docker-compose.yml copiado${NC}"
fi

# Backup do banco Redis (se estiver rodando)
echo -e "\n${YELLOW}Backup do Redis...${NC}"
if docker ps --format '{{.Names}}' | grep -q "redis"; then
    docker exec redis redis-cli BGSAVE > /dev/null 2>&1 || true
    sleep 2
    docker cp redis:/data/dump.rdb "$BACKUP_PATH/redis_dump.rdb" 2>/dev/null || true
    echo -e "${GREEN}✓ Redis dump salvo${NC}"
else
    echo -e "${YELLOW}! Redis nao esta rodando, pulando...${NC}"
fi

# Criar arquivo de manifesto
cat > "$BACKUP_PATH/MANIFEST.txt" << EOF
Alakoro FiberSense Backup
==========================
Data: $(date)
Hostname: $(hostname)
Usuario: $(whoami)
Versao: 2.0.0

Arquivos incluidos:
- uploads/ - Arquivos carregados
- exports/ - Arquivos exportados
- .env - Configuracoes de ambiente
- docker-compose.yml - Configuracao Docker
- redis_dump.rdb - Dump do Redis (se disponivel)
EOF

# Compactar
echo -e "\n${YELLOW}Compactando backup...${NC}"
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"

echo -e "\n========================================"
echo -e "${GREEN}Backup concluido!${NC}"
echo "Arquivo: ${BACKUP_NAME}.tar.gz"
echo "Local: $BACKUP_DIR"
echo "Tamanho: $(du -h ${BACKUP_NAME}.tar.gz | cut -f1)"
echo "========================================"
