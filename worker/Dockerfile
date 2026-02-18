
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for psycopg2 compilation if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY scripts/ ./scripts/
COPY worker/ ./worker/
# Copy config if needed (though it uses env vars mostly)

# Expose port (default 8000, but will be set by Cloud Provider env var PORT)
EXPOSE 8000

# Command to run the worker
CMD ["sh", "-c", "uvicorn worker.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
