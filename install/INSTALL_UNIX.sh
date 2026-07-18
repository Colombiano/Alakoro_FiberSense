#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Alakoro FiberSense — Instalador Automático macOS/Linux
# Automatic macOS/Linux Installer
# ═══════════════════════════════════════════════════════════════════

set -e

# Cores / Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║   🎸  ALAKORO FIBERSENSE v2.2.1                             ║${NC}"
echo -e "${BLUE}║      Plataforma DFOS para Poços de Petróleo                  ║${NC}"
echo -e "${BLUE}║      DFOS Platform for Oil & Gas Wells                       ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar Python
echo -e "${YELLOW}🔍 Verificando Python... / Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado! / Python3 not found!${NC}"
    echo ""
    echo "🌐 Instale Python em: / Install Python at:"
    echo "   macOS: brew install python3"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "   Fedora: sudo dnf install python3"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Python detectado: / Python detected:${NC}"
python3 --version
echo ""

# Criar ambiente virtual
echo -e "${YELLOW}📦 Criando ambiente virtual... / Creating virtual environment...${NC}"
python3 -m venv alakoro_env

# Ativar ambiente
echo -e "${YELLOW}⚡ Ativando ambiente... / Activating environment...${NC}"
source alakoro_env/bin/activate

# Atualizar pip
echo -e "${YELLOW}⬆️  Atualizando pip... / Upgrading pip...${NC}"
pip install --upgrade pip

# Instalar dependências
echo -e "${YELLOW}📥 Instalando dependências... / Installing dependencies...${NC}"
pip install -r requirements.txt

# Criar script de ativação
echo -e "${YELLOW}🖥️  Criando atalho... / Creating shortcut...${NC}"
cat > Alakoro_FiberSense.sh << 'EOF'
#!/bin/bash
source "$(dirname "$0")/alakoro_env/bin/activate"
python -c "from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig; from src.validation import SignatureValidator; from src.processing import LFDASProcessor; print('🎸 Alakoro FiberSense v2.2.1 pronto! / ready!')"
EOF
chmod +x Alakoro_FiberSense.sh

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ INSTALAÇÃO CONCLUÍDA! / INSTALLATION COMPLETE!          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🎸 Para usar o Alakoro FiberSense:${NC}"
echo -e "${BLUE}   To use Alakoro FiberSense:${NC}"
echo ""
echo "   1. Execute: ./Alakoro_FiberSense.sh"
echo "      Run: ./Alakoro_FiberSense.sh"
echo ""
echo "   2. Ou ative manualmente / Or activate manually:"
echo "      source alakoro_env/bin/activate"
echo "      python -c "from src.simulation import SignatureGenerator; ...""
echo ""
echo -e "${BLUE}📚 Documentação: README.md${NC}"
echo -e "${BLUE}🧪 Testes: pytest tests/ -v${NC}"
echo ""
