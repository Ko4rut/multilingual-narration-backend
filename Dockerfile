FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Normalize shell-script line endings so Windows CRLF checkouts cannot break /usr/bin/env.
RUN sed -i 's/\r$//' scripts/wait_for_postgres.sh && chmod +x scripts/wait_for_postgres.sh

CMD ["sh", "-c", "./scripts/wait_for_postgres.sh alembic upgrade head && python scripts/seed.py"]
