FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Iranian servers: pass a PyPI mirror (see docs/DEPLOY.md)
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --index-url "$PIP_INDEX_URL" -r requirements.txt

COPY . .

RUN useradd --create-home appuser && mkdir -p /app/media /app/staticfiles \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
