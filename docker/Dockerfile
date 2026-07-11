# Alakoro FiberSense - Dockerfile
# Multi-stage build para otimizacao

# ==================== Stage 1: Builder ====================
FROM python:3.11-slim as builder

# Instala dependencias de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libeigen3-dev \
    libhdf5-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Diretorio de trabalho
WORKDIR /build

# Copia arquivos do projeto
COPY CMakeLists.txt .
COPY setup.py .
COPY pyproject.toml .
COPY src/cpp ./src/cpp
COPY src/python ./src/python

# Instala pybind11
RUN pip install --no-cache-dir pybind11 numpy

# Build dos bindings C++
RUN mkdir build && cd build && \
    cmake .. -DBUILD_TESTS=OFF && \
    make -j$(nproc)

# ==================== Stage 2: Runtime ====================
FROM python:3.11-slim as runtime

LABEL maintainer="Luiz Paulo Colombiano"
LABEL description="Alakoro FiberSense - Sistema de Processamento DAS"
LABEL version="1.0.0"

# Instala dependencias de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libeigen3-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Diretorio da aplicacao
WORKDIR /app

# Copia artefatos do builder
COPY --from=builder /build/build ./build
COPY --from=builder /build/src ./src

# Copia arquivos Python
COPY setup.py .
COPY pyproject.toml .
COPY README.md .
COPY config ./config
COPY scripts ./scripts

# Instala dependencias Python
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    matplotlib \
    h5py \
    pyyaml \
    fastapi \
    uvicorn \
    websockets \
    pydantic \
    redis \
    pika \
    pybind11

# Compila e instala o pacote
RUN pip install -e .

# Portas expostas
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import alakoro; print('OK')" || exit 1

# Comando padrao
CMD ["python", "-m", "uvicorn", "src.python.api:app", "--host", "0.0.0.0", "--port", "8000"]
