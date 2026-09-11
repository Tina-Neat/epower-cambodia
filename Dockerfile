# Dockerfile for E-Power Cambodia Electricity Management System
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage directory for persistent SQLite database
RUN mkdir -p /app/data

EXPOSE 8000

# Healthcheck to verify system is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/login || exit 1

# Start Uvicorn bound to 0.0.0.0 on dynamically provided $PORT
CMD ["sh", "-c", "uvicorn web_app:app --host 0.0.0.0 --port ${PORT}"]
