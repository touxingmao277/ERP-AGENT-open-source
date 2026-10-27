"""FastAPI app factory for the local ERP test double."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routes import inventory, orders, parts, suppliers
from .schemas import envelope
from .store import ConflictError, NotFoundError, TestERPStore, ValidationError


def create_app(store: TestERPStore | None = None) -> FastAPI:
    app = FastAPI(title="ERP Test Double", version="1.0.0")
    app.state.store = store if store is not None else TestERPStore()

    @app.get("/health")
    def health():
        return envelope({"status": "ok"})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content=envelope(None, 404, str(exc)))

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=400, content=envelope(None, 400, str(exc)))

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content=envelope(None, 409, str(exc)))

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(status_code=400, content=envelope({"errors": details}, 400, "invalid request"))

    app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"])
    app.include_router(parts.router, prefix="/api/parts", tags=["parts"])
    app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
    app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
    return app
