from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..schemas import envelope

router = APIRouter()


@router.get("/warning")
def inventory_warning(request: Request):
    return envelope(request.app.state.store.inventory_warning())


@router.get("/page")
def inventory_page(
    request: Request,
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    partName: str | None = None,
    warehouseLocation: str | None = None,
):
    return envelope(request.app.state.store.inventory_page(current, size, partName, warehouseLocation))


@router.get("/check")
def inventory_check(request: Request):
    return envelope(request.app.state.store.inventory_check())


@router.post("/inbound")
def inventory_inbound(
    request: Request,
    partId: int = Query(ge=1),
    quantity: int = Query(gt=0),
    warehouseLocation: str | None = None,
):
    return envelope(request.app.state.store.inbound(partId, quantity, warehouseLocation))


@router.post("/outbound")
def inventory_outbound(
    request: Request,
    partId: int = Query(ge=1),
    quantity: int = Query(gt=0),
):
    return envelope(request.app.state.store.outbound(partId, quantity))


@router.get("/get/{id}")
def inventory_get(id: int, request: Request):
    return envelope(request.app.state.store.get_inventory(id))
