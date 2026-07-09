import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config  # noqa: F401 - loads .env before anything reads os.environ
from app.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="PourSight API")

# Wide open for local dev (Vite on a different port than uvicorn). The single-service
# production deploy serves the frontend from this same origin, so CORS won't matter there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Single-service deploy: FastAPI serves the built frontend from the same origin as the
# API, so there's no CORS/proxy to configure in production. Registered after the API
# router so /api/* still resolves first; only mounted if the build actually exists
# (keeps local backend-only dev working without requiring `npm run build` first).
FRONTEND_DIST = config.REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
