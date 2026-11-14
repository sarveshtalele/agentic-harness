# Agentic QE Platform: one custom container for Azure App Service (existing B1 plan), image in GHCR.
# Build (repo root):  docker build -f deploy/azure/Dockerfile -t agentic-qe .
# Two processes, as on the zip deployment: the API (FastAPI) on 127.0.0.1:8000 and the UI (Next.js) on 0.0.0.0:3000.
# The UI is the public port (WEBSITES_PORT=3000) and proxies /api/* to the API over loopback, so the API is never exposed.
# Size estimate: about 5 GB uncompressed (Playwright base 2 GB, JDK 0.4, .NET SDK 0.7, Go 0.25, Node 0.2, Python deps 0.8,
# UI 0.2), about 2 GB compressed in GHCR. App Service on B1 (10 GB local disk for images) holds it.

# ---- UI build: the backend URL is baked into the Next.js rewrites, so it is the loopback address of this container ----
FROM node:22.12.0-bookworm-slim AS ui
WORKDIR /opt/ui
ENV NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=2048 ATLAS_STANDALONE=1 ATLAS_BACKEND_URL=http://127.0.0.1:8000
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY src/frontend/ ./
RUN npm run build \
 && cp -rL .next/standalone /opt/ui-run \
 && mkdir -p /opt/ui-run/.next && cp -r .next/static /opt/ui-run/.next/static \
 && { [ ! -d public ] || cp -r public /opt/ui-run/public; }

# ---- Runtime ----
# Tag matches the playwright version in the requirements (1.65). Released well over two weeks before 2026-11-14.
FROM mcr.microsoft.com/playwright/python:v1.65.0-noble
ARG TARGETARCH=amd64
ARG NODE_VERSION=22.12.0
ARG GO_VERSION=1.23.4
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 NEXT_TELEMETRY_DISABLED=1 \
    GOPATH=/home/atlas/go PATH=/usr/local/go/bin:/opt/venv/bin:$PATH

USER root
# JDK 21 and .NET SDK 8 from the Ubuntu 24.04 archive; git and curl for repository cloning and the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates xz-utils python3-venv openjdk-21-jdk-headless dotnet-sdk-8.0 \
 && rm -rf /var/lib/apt/lists/*
# Node 22 (official tarball) and Go (official tarball), pinned
RUN case "$TARGETARCH" in arm64) N=arm64; G=arm64;; *) N=x64; G=amd64;; esac \
 && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${N}.tar.xz" | tar -xJ -C /usr/local --strip-components=1 \
 && curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${G}.tar.gz" | tar -xz -C /usr/local

WORKDIR /app
# venv shares the base image's Playwright (same version as the browsers in /ms-playwright)
COPY requirements.txt ./
RUN python3 -m venv --system-site-packages /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt \
 && /opt/venv/bin/python -c "import playwright, sys; print('playwright', playwright.__version__)"
COPY src/backend /app/src/backend
COPY prompts /app/prompts
COPY templates /app/templates
COPY skills /app/skills
COPY evals /app/evals
COPY plugins/agentic-qe /app/plugins/agentic-qe
COPY scripts/env_check.py scripts/sqlite_to_postgres.py /app/scripts/
COPY --from=ui /opt/ui-run /opt/ui
COPY deploy/azure/container_start.py /app/container_start.py

# Non-root. /home/atlas is replaced by the persistent App Service /home share at run time (WEBSITES_ENABLE_APP_SERVICE_STORAGE=true).
RUN mkdir -p /home/atlas/data && chown -R pwuser:pwuser /home/atlas /app /opt/ui
USER pwuser
ENV PYTHONPATH=/app/src:/app ATLAS_PROFILE=web ATLAS_HOME=/home/atlas ATLAS_DATA_DIR=/home/atlas/data \
    ATLAS_MAX_SANDBOXES=5 WEBSITES_PORT=3000 PORT=3000

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:3000/api/health || exit 1
ENTRYPOINT ["python3", "/app/container_start.py"]
