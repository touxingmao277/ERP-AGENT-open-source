from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, Request

from ..schemas import OrderWrite, envelope

router = APIRouter()


@router.post("/create")
def order_create(payload: OrderWrite, request: Request):
    return envelope(request.app.state.store.create_order(payload.model_dump(exclude_none=True)))


@router.put("/update/{id}")
def order_update(id: int, payload: OrderWrite, request: Request):
    return envelope(request.app.state.store.update_order(id, payload.model_dump(exclude_none=True)))


@router.get("/page")
def order_page(
    request: Request,
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    orderNumber: str | None = None,
    status: int | None = Query(default=None, ge=0, le=4),
    startDate: date | None = None,
    endDate: date | None = None,
):
    return envelope(request.app.state.store.order_page(
        current, size, orderNumber,
        status,
        startDate.isoformat() if startDate else None,
        endDate.isoformat() if endDate else None,
    ))


@router.get("/get/{id}")
def order_get(id: int, request: Request):
    return envelope(request.app.state.store.get_order(id))


@router.get("/search-details")
def order_search_details(
    request: Request,
    partName: str | None = None,
    startDate: date | None = None,
    endDate: date | None = None,
):
    return envelope(request.app.state.store.order_search_details(
        partName,
        startDate.isoformat() if startDate else None,
        endDate.isoformat() if endDate else None,
    ))


@router.get("/statistics")
def order_statistics(
    request: Request,
    startDate: date | None = None,
    endDate: date | None = None,
):
    return envelope(request.app.state.store.order_statistics(
        startDate.isoformat() if startDate else None,
        endDate.isoformat() if endDate else None,
    ))


@router.patch("/update-status/{id}")
def order_update_status(
    id: int, request: Request, status: int = Query(ge=0, le=4)
):
    return envelope(request.app.state.store.update_order_status(id, status))
