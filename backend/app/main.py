from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    analyses,
    auth,
    dashboard,
    issues,
    project_data,
    projects,
    repositories,
    reports,
)
from app.core.config import Settings, settings
from app.core.errors import register_error_handlers
from app.services import analysis_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    analysis_service.fail_interrupted_analyses()
    yield


_dev = settings.app_env == "development"

app = FastAPI(
    title="CodeScope API",
    description="Understand your codebase. Improve your engineering.",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs are a development tool; they are not exposed in production.
    docs_url="/docs" if _dev else None,
    redoc_url=None,
    openapi_url="/openapi.json" if _dev else None,
)

def cors_options(s: Settings) -> dict:
    """CORS only matters when the web app is on another origin than the API (Vercel + Render)."""
    return {
        "allow_origins": s.cors_origin_list,
        # Starlette matches this with fullmatch, so "evil-yourapp.vercel.app" cannot slip through.
        "allow_origin_regex": s.cors_origin_regex or None,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }


app.add_middleware(CORSMiddleware, **cors_options(settings))

register_error_handlers(app)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(projects.router)
api.include_router(project_data.router)
api.include_router(repositories.router)
api.include_router(analyses.router)
api.include_router(reports.router)
api.include_router(issues.router)
api.include_router(dashboard.router)
app.include_router(api)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
