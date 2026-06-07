"""FastAPI app factory and lifecycle."""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.adapters.storage.minio_store import MinioObjectStore
from filternarrange_engine.application.convert_service import ConvertService
from filternarrange_engine.application.detect_service import DetectService
from filternarrange_engine.application.filter_service import FilterService
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError
from filternarrange_engine.platform.logging import configure_logging

from .dependencies import trace_id_var
from .routes_convert import router as convert_router
from .routes_detect import router as detect_router
from .routes_filter import router as filter_router


def build_app(store=None, registry: PluginRegistry | None = None,
              settings: EngineSettings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or EngineSettings()
    registry = registry or PluginRegistry()
    if registry.list_formats() == [] and store is None:
        registry.discover()
    store = store or MinioObjectStore(settings)

    app = FastAPI(title="FilterNArrange data-engine", version="1.0.0")
    app.state.settings = settings
    app.state.registry = registry
    app.state.store = store
    app.state.detect = DetectService(store, registry, settings)
    app.state.filter = FilterService(store, registry)
    app.state.convert = ConvertService(store, registry, settings)

    app.include_router(detect_router)
    app.include_router(filter_router)
    app.include_router(convert_router)

    @app.exception_handler(EngineError)
    async def engine_error_handler(request: Request, exc: EngineError):
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "pluginId": exc.plugin_id,
                "message": exc.message,
                "traceId": trace_id_var.get() or "unknown",
            },
        )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "formats": registry.list_formats(),
                "filters": registry.list_filters()}

    return app


app = build_app()
