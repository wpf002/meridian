# syntax=docker/dockerfile:1

# --- Stage 1: build the React/Vite frontend --------------------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /app/frontend/dist

# --- Stage 2: Python runtime serving the API + built frontend --------------
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_HOST=0.0.0.0

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
# Overlay the freshly built frontend (the local one is .dockerignored).
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Railway provides $PORT; api/__main__ binds it.
CMD ["python", "-m", "api"]
