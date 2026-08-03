from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.exceptions import ApiError
from api.models import ErrorDetail, ErrorEnvelope, HealthResponse


def create_app() -> FastAPI:
    """FastAPI application factory.

    All routers are mounted here. Using a factory (not a module-level
    app instance) keeps TestClient setup clean in tests.
    """
    app = FastAPI(
        title="Commodity Systematic Research Platform API",
        version="0.1.0",
        description=(
            "Thin HTTP boundary over the commodity research src/ library. "
            "Route handlers perform no computation — they parse, call one "
            "src/ function, and serialize."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                detail=exc.detail,
                field_errors=exc.field_errors,
            )
        )
        return JSONResponse(status_code=exc.status, content=envelope.model_dump())

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Health check. Used by the frontend TopBar health indicator."""
        return HealthResponse(status="ok", version="0.1.0", backend_tests=267)

    from api.routers import assets as assets_router
    from api.routers import backtests as backtests_router
    from api.routers import curves as curves_router
    from api.routers import features as features_router
    from api.routers import intelligence as intelligence_router
    from api.routers import portfolio as portfolio_router
    from api.routers import runs as runs_router
    from api.routers import signals as signals_router
    from api.routers import sweeps as sweeps_router
    from api.routers import system as system_router
    from api.routers import validation as validation_router

    app.include_router(assets_router.router)
    app.include_router(backtests_router.router)
    app.include_router(features_router.router)
    app.include_router(portfolio_router.router)
    app.include_router(runs_router.router)
    app.include_router(signals_router.router)
    app.include_router(system_router.router)
    app.include_router(curves_router.router)
    app.include_router(validation_router.router)
    app.include_router(sweeps_router.router)
    app.include_router(intelligence_router.router)

    return app


# Module-level instance for uvicorn: `uvicorn api.main:app`
app = create_app()
