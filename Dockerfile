# The Node stage builds the frontend, then the Python stage serves both frontend and API.
FROM node:22-bookworm-slim AS ui
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Chromium and OS dependencies preinstalled; version must match Python package.
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ /app/backend/
COPY --from=ui /app/frontend/dist /app/frontend/dist
# Never run the browser as root. Hosting must permit Chrome user namespace sandbox.
RUN useradd -m -s /bin/bash airlock && chown -R airlock:airlock /app
USER airlock
ENV PYTHONUNBUFFERED=1
ENV AIRLOCK_DEV_NO_BROWSER_SANDBOX=0
ENV AIRLOCK_ENABLE_URL_SCAN=0
ENV PORT=8000
EXPOSE 8000
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn airlock.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
