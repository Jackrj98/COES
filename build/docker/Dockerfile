# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

ENV APP_HOME=/app/coes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dependencias de compilación (solo existen en esta etapa, no llegan a la imagen final)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $APP_HOME

# Copiar solo requirements primero -> aprovecha cache de Docker si el código cambia pero no las deps
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt

# gunicorn se instala aquí junto con el resto -> una sola capa, mismo --user
RUN pip install --upgrade pip \
    && pip install --user --no-cache-dir -r requirements/prod.txt gunicorn

# Copiar el resto del código (usa un .dockerignore para excluir .git, tests, __pycache__, etc.)
COPY . .


# ---------- Final stage ----------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOME=/app/coes \
    PATH="/home/appuser/.local/bin:${PATH}"

# Solo la librería runtime de PostgreSQL (libpq5), NO libpq-dev (que trae headers de compilación)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    make \
    gettext \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

WORKDIR $APP_HOME

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --from=builder --chown=appuser:appuser $APP_HOME $APP_HOME

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/', timeout=3).status==200 else 1)" || exit 1

#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]