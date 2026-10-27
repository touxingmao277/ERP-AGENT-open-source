from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..schemas import PartCreate, envelope

router = APIRouter()


@router.get("/get/{id}")
def part_get(id: int, request: Request):
    return envelope(request.app.state.store.get_part(id))


@router.get("/search")
def part_search(request: Request, name: str = Query(min_length=1)):
    return envelope(request.app.state.store.part_search(name))


@router.get("/supplier/{supplier_id}")
def parts_by_supplier(supplier_id: int, request: Request):
    request.app.state.store.get_supplier(supplier_id)
    return envelope(request.app.state.store.parts_by_supplier(supplier_id))


@router.get("/page")
def part_page(
    request: Request,
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    name: str | None = None,
    category: str | None = None,
    supplierId: int | None = Query(default=None, ge=1),
):
    return envelope(request.app.state.store.part_page(current, size, name, category, supplierId))


@router.post("/create")
def part_create(payload: PartCreate, request: Request):
    return envelope(request.app.state.store.create_part(payload.model_dump(exclude_none=True)))
