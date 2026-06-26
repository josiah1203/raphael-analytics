"""Raphael service: raphael-analytics."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from raphael_contracts.errors import ErrorResponse
from raphael_analytics.routes import router

app = FastAPI(
    title="raphael-analytics",
    description="Usage, business, and organizational intelligence",
    version="0.1.0",
    openapi_url="/v1/analytics/openapi.json" if "/v1/analytics" else "/openapi.json",
)

app.include_router(router, prefix="/v1/analytics" if "/v1/analytics" else "")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "raphael-analytics"}


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception) -> JSONResponse:
    err = ErrorResponse(code="internal_error", message=str(exc))
    return JSONResponse(status_code=500, content=err.model_dump())
