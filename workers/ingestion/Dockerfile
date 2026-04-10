FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libmagic1 poppler-utils tesseract-ocr \
  && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --upgrade pip && pip install ".[dev]"

CMD ["celery", "-A", "app.worker", "worker", "--loglevel=INFO", "-Q", "ingestion,api"]
