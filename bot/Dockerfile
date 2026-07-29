# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir "httpx>=0.27.0" \
    && groupadd --system bot && useradd --system --gid bot --home /app bot

COPY bot.py ./

USER bot

CMD ["python", "bot.py"]
