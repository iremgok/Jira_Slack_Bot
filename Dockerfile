FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src

# Run as an unprivileged user
RUN useradd --create-home --uid 1000 bot && mkdir -p /app/logs && chown -R bot /app
USER bot

CMD ["python", "-m", "src.main"]
