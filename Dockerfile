# ═══════════════════════════════════════════════════════════════════
# Alakoro FiberSense — Dockerfile
# Ambiente containerizado para DFOS em Poços de Petróleo
# Containerized environment for DFOS in Oil & Gas Wells
# ═══════════════════════════════════════════════════════════════════

FROM python:3.11-slim

LABEL maintainer="Luiz Paulo Colombiano"
LABEL version="2.2.1"
LABEL description="Alakoro FiberSense — DFOS Platform / Plataforma DFOS"

# ─── Instalar dependências do sistema / System dependencies ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# ─── Diretório de trabalho / Working directory ───
WORKDIR /app

# ─── Instalar Alakoro FiberSense via pip / Install via pip ───
# Em produção, use a versão do PyPI:
# RUN pip install --no-cache-dir alakoro-fibersense==2.2.1
# 
# Para desenvolvimento, copie o código local:
COPY . /app/
RUN pip install --no-cache-dir -e .

# ─── Variáveis de ambiente / Environment variables ───
ENV PYTHONPATH=/app
ENV ALAKORO_VERSION=2.2.1
ENV ALAKORO_LANG=pt

# ─── Health check / Health check ───
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.simulation import SignatureGenerator; print('OK')" || exit 1

# ─── Comando padrão / Default command ───
CMD ["python", "-c", \
    "from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig; \
     from src.validation import SignatureValidator; \
     from src.processing import LFDASProcessor; \
     print('🎸 Alakoro FiberSense v2.2.1 pronto / ready!')"]
