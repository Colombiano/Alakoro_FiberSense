# ═══════════════════════════════════════════════════════════════════
# Alakoro FiberSense — Dockerfile
# Ambiente containerizado para DFOS em Pocos de Petroleo
# Containerized environment for DFOS in Oil & Gas Wells
# ═══════════════════════════════════════════════════════════════════

FROM python:3.11-slim

LABEL maintainer="Luiz Paulo Colombiano"
LABEL version="2.11.0"
LABEL description="Alakoro FiberSense — DFOS Platform / Plataforma DFOS"

# ─── Instalar dependencias do sistema / System dependencies ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    ninja-build \
    protobuf-compiler \
    libprotobuf-dev \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# ─── Diretorio de trabalho / Working directory ───
WORKDIR /app

# ─── Copiar codigo local / Copy local code ───
COPY . /app/

# ─── Instalar Alakoro FiberSense / Install Alakoro FiberSense ───
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . \
        --config-settings=cmake.define.ALAKORO_WITH_PROTOBUF=ON

# ─── Variaveis de ambiente / Environment variables ───
ENV PYTHONPATH=/app
ENV ALAKORO_VERSION=2.11.0
ENV ALAKORO_LANG=pt
ENV QT_QPA_PLATFORM=offscreen

# ─── Health check / Health check ───
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.simulation import SignatureGenerator; print('OK')" || exit 1

# ─── Comando padrao / Default command ───
CMD ["python", "-c", \
    "from src.simulation import SignatureGenerator, WellGeometry, AcquisitionConfig; \
     from src.validation import SignatureValidator; \
     from src.processing import LFDASProcessor; \
     print('🎸 Alakoro FiberSense v2.11.0 pronto / ready!')"]
