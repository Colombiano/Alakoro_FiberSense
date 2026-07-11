# Multi-stage build
FROM python:3.11-slim as cpp-builder

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY engine/ ./engine/
RUN cd engine && mkdir build && cd build && cmake .. && make -j$(nproc)

# Python stage
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=cpp-builder /build/engine/build/*.so /app/engine/
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
