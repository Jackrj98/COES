# ==========================================
# Builder stage
# ==========================================
FROM python:3.11-slim AS builder

ENV APP_HOME=/app/coes

RUN chmod 1777 /tmp

# Instalar dependencias del sistema necesarias para compilar paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    build-essential \
    pkg-config \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $APP_HOME

# Copiar primero los requirements para aprovechar la caché de Docker
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt

# Instalar dependencias de Python para el usuario actual
RUN pip install --upgrade pip \
    && pip install --user --no-cache-dir -r requirements/prod.txt

COPY manage.py ./
COPY apps/ ./apps/
COPY build/ ./build/
COPY cfg/ ./cfg/
COPY makefile/ ./makefile/
COPY locale/ ./locale/
COPY templates/ ./templates/
COPY static/ ./static/


# ==========================================
# Final stage
# ==========================================
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app/coes
ENV PATH="/root/.local/bin:${PATH}"

# Instalar únicamente dependencias de runtime (sin herramientas de compilación pesadas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $APP_HOME

# Copiar los paquetes de Python instalados desde el builder
COPY --from=builder /root/.local /root/.local

# Copiar el código de la aplicación ya compilado/preparado desde el builder
COPY --from=builder $APP_HOME $APP_HOME

# Exponer el puerto de la aplicación
EXPOSE 8000