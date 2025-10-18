# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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

COPY pyproject.toml README.md LICENSE AGENTS.md ./
COPY src ./src

ARG INSTALL_EXTRAS=""
RUN pip install --upgrade pip \
 && if [ -n "${INSTALL_EXTRAS}" ]; then \
      pip install ".[${INSTALL_EXTRAS}]"; \
    else \
      pip install .; \
    fi

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local /usr/local

WORKDIR /app
COPY src ./src
COPY README.md LICENSE pyproject.toml trip_planner.ipynb ./
COPY docs ./docs

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
