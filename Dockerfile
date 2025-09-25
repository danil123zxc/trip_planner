# syntax=docker/dockerfile:1.6
FROM python:3.10-slim AS base

# Avoid interactive prompts and enable faster pip installs
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies for scientific/python tooling and unstructured parsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    wget \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies early for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout=300 -r requirements.txt

# Copy project sources
COPY src ./src
COPY AGENTS.md ./AGENTS.md
COPY README.md ./README.md

# Expose FastAPI port
EXPOSE 8000

# Default entrypoint runs the FastAPI app
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
