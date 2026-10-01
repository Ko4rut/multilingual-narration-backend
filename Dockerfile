FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# docker-compose gates db-init on PostgreSQL's healthcheck, so no executable
# wait script is needed here. This also avoids Windows CRLF/shebang issues.
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed.py"]
