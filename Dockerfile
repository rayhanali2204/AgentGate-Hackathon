# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Empty base means relative /api URLs. Local .env files are excluded from context.
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FRONTEND_DIST_PATH=/app/frontend/dist
WORKDIR /app/backend

# Cache runtime dependencies separately from frequently changing application code.
COPY backend/pyproject.toml ./
RUN python -c "import subprocess, sys, tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', *deps])"
COPY backend/app/ ./app/
RUN python -m pip install --no-cache-dir --no-deps . \
    && groupadd --gid 10001 agentgate \
    && useradd --uid 10001 --gid agentgate --no-create-home --shell /usr/sbin/nologin agentgate
COPY --from=frontend-build /build/frontend/dist/ /app/frontend/dist/

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import json, urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3); assert json.load(response)['status'] == 'ok'"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
