# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for NestedTune Guard.
#
# Stage 1 (python-builder): installs Python deps + the nestedtune_guard package
# Stage 2 (node-builder): builds the Next.js dashboard for production
# Stage 3 (runtime):      combines Python + Node runtime + dashboard
#
# Final image runs both the Next.js dashboard (port 3000) and the Python
# CLI (used internally by the dashboard's /api/simulate route).

ARG PYTHON_VERSION=3.11
ARG NODE_VERSION=20
ARG BUN_VERSION=1.3.9

# ----------------------------------------------------------------------------
# Stage 1: Python builder
# ----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS python-builder

# Install pytest and any other build/runtime deps. The package itself is
# dependency-light (only stdlib), but pytest is required for the gate.
RUN pip install --no-cache-dir pytest

# Copy the Python package source. The CLI expects `PYTHONPATH=src` in dev
# but in the container we install it under site-packages so it's importable
# without PYTHONPATH manipulation.
WORKDIR /app
COPY nestedtune_guard ./nestedtune_guard
COPY fixtures ./fixtures
COPY scripts ./scripts
COPY tests ./tests

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run the gate as a build-time smoke test. If it fails, the image build fails.
RUN PYTHONPATH=/app python3 -m nestedtune_guard.cli gate

# ----------------------------------------------------------------------------
# Stage 2: Node builder
# ----------------------------------------------------------------------------
FROM oven/bun:${BUN_VERSION}-slim AS node-builder

WORKDIR /app

# Copy package manifests first for better layer caching.
COPY package.json bun.lock ./
COPY prisma ./prisma
# Install the exact dependency graph captured by the repository lockfile.
RUN bun install --frozen-lockfile

# Copy the rest of the source and build for production.
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

# ----------------------------------------------------------------------------
# Stage 3: Runtime
# ----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-slim AS runtime

# Install Python runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir --break-system-packages pytest

WORKDIR /app

# Copy built Next.js artifacts
COPY --from=node-builder /app/.next ./.next
COPY --from=node-builder /app/public ./public
COPY --from=node-builder /app/download ./download
COPY --from=node-builder /app/package.json ./package.json
COPY --from=node-builder /app/node_modules ./node_modules
COPY --from=node-builder /app/next.config.ts ./

# Copy Python package + fixtures
COPY --from=python-builder /app/nestedtune_guard ./nestedtune_guard
COPY --from=python-builder /app/fixtures ./fixtures
COPY --from=python-builder /app/scripts ./scripts
COPY --from=python-builder /app/tests ./tests

ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

# Health check: hits the dashboard's /api/health endpoint, which verifies
# both Python and the package are importable.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/api/health').then(r => r.json()).then(d => process.exit(d.ok ? 0 : 1)).catch(() => process.exit(1))"

# Run the Next.js server. The dashboard's API routes spawn the Python CLI
# as a subprocess when /api/simulate is called.
CMD ["npm", "start"]
