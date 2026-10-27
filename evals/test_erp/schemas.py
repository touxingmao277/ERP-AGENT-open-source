"""Shared HTTP request models and response helpers."""
from __future__ import annotations

from math import ceil
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplierCode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    contactPerson: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    creditRating: str | None = Field(default=None, pattern="^[ABCD]$")
    status: int = Field(default=1, ge=0, le=1)


class PartCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partCode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    purchasePrice: float = Field(ge=0)
    model: str | None = None
    specification: str | None = None
    unit: str | None = None
    suggestedRetailPrice: float | None = Field(default=None, ge=0)
    stockWarningValue: int | None = Field(default=None, ge=0)
    supplierId: int | None = Field(default=None, ge=1)
    category: str | None = None
    description: str | None = None


class OrderDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partId: int = Field(ge=1)
    quantity: int = Field(ge=1)
    unitPrice: float = Field(gt=0)
    remark: str | None = None


class OrderWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orderNumber: str = Field(min_length=1, max_length=64)
    totalAmount: float | None = Field(default=None, ge=0)
    status: int = Field(default=0, ge=0, le=4)
    orderTime: str | None = None
    remark: str | None = None
    orderDetail: list[OrderDetail] = Field(min_length=1)


def envelope(data: Any, code: int = 200, message: str = "success") -> dict:
    return {"code": code, "message": message, "data": data}


def page(records: list[dict], current: int, size: int) -> dict:
    if current < 1 or size < 1 or size > 100:
        raise ValueError("current must be >= 1 and size must be between 1 and 100")
    total = len(records)
    start = (current - 1) * size
    return {
        "records": records[start:start + size],
        "total": total,
        "current": current,
        "size": size,
        "pages": ceil(total / size) if total else 0,
    }
