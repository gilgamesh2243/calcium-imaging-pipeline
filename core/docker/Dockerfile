FROM python:3.11-slim

WORKDIR /app

# Install protoc (for grpc_tools.protoc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Copy proto file first (for proto code generation)
COPY proto/ /app/proto/

# Install Python dependencies
COPY core/pyproject.toml /app/
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || true
COPY core/ /app/

RUN pip install --no-cache-dir -e "."

ENV QC_CONFIG_ROOT=/app/configs
ENV QC_GRPC_PORT=50051
ENV QC_HTTP_PORT=8000

EXPOSE 50051 8000

CMD ["python", "-m", "qc_core.main"]
