# Multi-stage build so the deployed image needs neither Node nor npm at
# runtime - just the built static frontend, served by FastAPI itself
# (single-service deploy: one process, one origin, no CORS/proxy to configure).

FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# The dataset and retrieval corpus are deterministic and reproducible, so bake
# them into the image at build time rather than needing a persistent volume.
WORKDIR /app/backend
RUN python -m app.db.seed && python -m app.retrieval.build_docs

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
