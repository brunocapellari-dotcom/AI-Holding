import logging
import uuid

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint

from app.api.routes import (
    agents,
    decisions,
    executive,
    holding,
    incidents,
    knowledge,
    pmo,
    policy,
    projects,
    runs,
    tasks,
)
from app.core.config import settings
from app.core.request_context import request_id_ctx
from app.db.session import engine
from app.observability import configure_observability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("holding-control-plane")

app = FastAPI(
    title=settings.app_name,
    version="2.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None,
)


@app.middleware("http")
async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "holding-control-plane"}


@app.get("/ready", tags=["system"])
def ready() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(projects.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(decisions.router, prefix=settings.api_prefix)
app.include_router(agents.router, prefix=settings.api_prefix)
app.include_router(runs.router, prefix=settings.api_prefix)
app.include_router(incidents.router, prefix=settings.api_prefix)
app.include_router(policy.router, prefix=settings.api_prefix)
app.include_router(pmo.router, prefix=settings.api_prefix)
app.include_router(executive.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(holding.router, prefix=settings.api_prefix)

configure_observability(app)
