from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..schemas import SupplierCreate, envelope

router = APIRouter()


@router.get("/search")
def supplier_search(request: Request, name: str = Query(min_length=1)):
    return envelope(request.app.state.store.supplier_search(name))


@router.get("/page")
def supplier_page(
    request: Request,
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    name: str | None = None,
    status: int | None = Query(default=None, ge=0, le=1),
    creditRating: str | None = Query(default=None, pattern="^[ABCD]$"),
):
    return envelope(request.app.state.store.supplier_page(current, size, name, status, creditRating))


@router.get("/get/{id}")
def supplier_get(id: int, request: Request):
    return envelope(request.app.state.store.get_supplier(id))


@router.post("/create")
def supplier_create(payload: SupplierCreate, request: Request):
    return envelope(request.app.state.store.create_supplier(payload.model_dump(exclude_none=True)))


@router.patch("/update-status/{id}")
def supplier_update_status(
    id: int, request: Request, status: int = Query(ge=0, le=1)
):
    return envelope(request.app.state.store.update_supplier_status(id, status))
