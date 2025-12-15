# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    git \
    git-lfs \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global user.email "docker@spienx.com" \
    && git config --global user.name "Spienx Docker"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Install project dependencies
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port for Django
EXPOSE 8000

# Default command - run Daphne ASGI server
CMD ["poetry", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
