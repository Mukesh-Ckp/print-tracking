"""
FastAPI application entry-point.

Bootstraps:
* Logging configuration
* Database table creation (idempotent)
* Default-admin and default-printer seeding
* CORS, request-logging middleware
* Registers all routers under the configured API prefix
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database.session import init_db
from .middleware.logging_middleware import RequestLoggingMiddleware
from .routers import auth, dashboard, prints, reports, stats, users
from .schemas.common import HealthResponse
from .utils.logging_config import configure_logging
from .utils.seed import ensure_default_admin, ensure_default_printer

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application start/stop lifecycle hooks."""
    logger.info("Starting %s (env=%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    init_db()
    ensure_default_admin()
    ensure_default_printer()
    logger.info("Application ready and accepting traffic.")
    yield
    logger.info("Application shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description=(
            "Enterprise Print Tracking & Monitoring System. "
            "Provides ingestion APIs for the on-premise Windows print-agent and "
            "JWT-secured REST APIs for the React admin dashboard."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- Middleware ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-ms"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ---- Routers ----
    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(prints.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(stats.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)

    # ---- Health & root ----
    @app.get("/", tags=["health"])
    def root():
        return JSONResponse(
            {
                "service": settings.PROJECT_NAME,
                "version": "1.0.0",
                "docs": "/docs",
                "health": "/health",
                "api_prefix": prefix,
            }
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    return app


app = create_app()
