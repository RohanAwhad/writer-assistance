# INT-006 container packaging (R-077): multi-stage, no compose (DEC-019).
# Stage 1 builds the SPA; stage 2 runs backend + built dist as non-root.
# No secrets are baked in (ASM-014): all runtime config arrives via -e/--env-file.

# ---- stage 1: build frontend/dist (R-077) -----------------------------------
FROM node:24-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: runtime (SD-25) -----------------------------------------------
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv pinned to the host toolchain (uv 0.11.16).
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

# Image layout (/app/backend + /app/frontend/dist) keeps the app factory's
# static default correct: app/main.py resolves Path(__file__).parents[2] ->
# /app, so the mount default is /app/frontend/dist (SD-25, R-076).
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app

COPY --from=frontend-build /frontend/dist /app/frontend/dist

# Non-root writer (uid 1000) owns /app; /data mountpoint chowned so a fresh
# named volume inherits writable ownership (SD-25, DEC-023).
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin writer \
    && mkdir -p /data \
    && chown -R writer:writer /app /data

USER writer

ENV PATH="/app/backend/.venv/bin:$PATH" \
    WRITER_ASSISTANCE_DB=/data/writer-assistance.db

EXPOSE 8000

# Fail-closed boot (R-078, SD-24): refuse to serve gate-open. The module app
# resolves AUTH_API_KEY at import; the image must never run with the gate
# inactive, so the key is required here and uvicorn only starts after the check.
CMD ["sh", "-c", "if [ -z \"${AUTH_API_KEY}\" ]; then echo 'AUTH_API_KEY is required: refusing to boot gate-open (R-078). Provide it via --env-file backend/.env or -e AUTH_API_KEY=...' >&2; exit 1; fi; exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"]
