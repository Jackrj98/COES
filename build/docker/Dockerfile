# Builder stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV APP_HOME=/app/coes

RUN chmod 1777 /tmp

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    pkg-config \
    libpq-dev \
    gettext \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR $APP_HOME

# Copy the requirements file into the container
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt

RUN pip install --upgrade pip \
    && pip install --user --no-cache-dir -r requirements/prod.txt

# Copy the current directory contents into the container
COPY . .

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app/coes
ENV PATH="/root/.local/bin:${PATH}"

# Install PostgreSQL runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev make\
     gettext \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR $APP_HOME

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder $APP_HOME $APP_HOME

# Install gunicorn
RUN pip install --no-cache-dir gunicorn

# Clean up
RUN rm -rf /root/.cache/pip

# Expose port
EXPOSE 8000