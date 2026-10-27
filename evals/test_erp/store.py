"""Thread-safe in-memory ERP domain store."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from threading import RLock
from typing import Any

from .seed_data import fresh_seed_data


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class TestERPStore:
    """Mutable process-local ERP state; a new instance starts from seed data."""

    def __init__(self, seed: dict[str, list[dict]] | None = None):
        data = deepcopy(seed) if seed is not None else fresh_seed_data()
        self._suppliers = data["suppliers"]
        self._parts = data["parts"]
        self._inventory = data["inventory"]
        self._orders = data["orders"]
        self._lock = RLock()
        self._next_ids = {
            name: max((row["id"] for row in rows), default=0) + 1
            for name, rows in (
                ("supplier", self._suppliers),
                ("part", self._parts),
                ("inventory", self._inventory),
                ("order", self._orders),
            )
        }

    def _id(self, kind: str) -> int:
        value = self._next_ids[kind]
        self._next_ids[kind] += 1
        return value

    @staticmethod
    def _copy(value):
        return deepcopy(value)

    @staticmethod
    def _contains(value: Any, needle: str) -> bool:
        return needle.casefold() in str(value or "").casefold()

    @staticmethod
    def _check_page(current: int, size: int) -> None:
        if current < 1 or size < 1 or size > 100:
            raise ValidationError("current must be >= 1 and size must be between 1 and 100")

    def _paginate(self, rows: list[dict], current: int, size: int) -> dict:
        self._check_page(current, size)
        total = len(rows)
        start = (current - 1) * size
        return {
            "records": self._copy(rows[start:start + size]),
            "total": total,
            "current": current,
            "size": size,
            "pages": (total + size - 1) // size if total else 0,
        }

    def supplier_search(self, name: str) -> list[dict]:
        with self._lock:
            return self._copy([r for r in self._suppliers if self._contains(r["name"], name)])

    def supplier_page(self, current=1, size=10, name=None, status=None, credit_rating=None) -> dict:
        with self._lock:
            rows = self._suppliers
            if name:
                rows = [r for r in rows if self._contains(r["name"], name)]
            if status is not None:
                rows = [r for r in rows if r["status"] == status]
            if credit_rating:
                rows = [r for r in rows if r.get("creditRating") == credit_rating]
            return self._paginate(rows, current, size)

    def get_supplier(self, supplier_id: int) -> dict:
        with self._lock:
            row = next((r for r in self._suppliers if r["id"] == supplier_id), None)
            if row is None:
                raise NotFoundError(f"supplier {supplier_id} not found")
            return self._copy(row)

    def create_supplier(self, payload: dict) -> dict:
        with self._lock:
            if any(r["supplierCode"] == payload["supplierCode"] for r in self._suppliers):
                raise ConflictError(f"supplierCode {payload['supplierCode']} already exists")
            row = {k: v for k, v in payload.items() if v is not None}
            row["id"] = self._id("supplier")
            row.setdefault("status", 1)
            self._suppliers.append(row)
            return self._copy(row)

    def update_supplier_status(self, supplier_id: int, status: int) -> dict:
        with self._lock:
            row = next((r for r in self._suppliers if r["id"] == supplier_id), None)
            if row is None:
                raise NotFoundError(f"supplier {supplier_id} not found")
            row["status"] = status
            return self._copy(row)

    def get_part(self, part_id: int) -> dict:
        with self._lock:
            row = next((r for r in self._parts if r["id"] == part_id), None)
            if row is None:
                raise NotFoundError(f"part {part_id} not found")
            return self._copy(row)

    def part_search(self, name: str) -> list[dict]:
        with self._lock:
            return self._copy([r for r in self._parts if self._contains(r["name"], name)])

    def parts_by_supplier(self, supplier_id: int) -> list[dict]:
        with self._lock:
            return self._copy([r for r in self._parts if r.get("supplierId") == supplier_id])

    def part_page(self, current=1, size=10, name=None, category=None, supplier_id=None) -> dict:
        with self._lock:
            rows = self._parts
            if name:
                rows = [r for r in rows if self._contains(r["name"], name)]
            if category:
                rows = [r for r in rows if self._contains(r.get("category"), category)]
            if supplier_id is not None:
                rows = [r for r in rows if r.get("supplierId") == supplier_id]
            return self._paginate(rows, current, size)

    def create_part(self, payload: dict) -> dict:
        with self._lock:
            if any(r["partCode"] == payload["partCode"] for r in self._parts):
                raise ConflictError(f"partCode {payload['partCode']} already exists")
            supplier_id = payload.get("supplierId")
            if supplier_id is not None and not any(s["id"] == supplier_id for s in self._suppliers):
                raise ValidationError(f"supplier {supplier_id} not found")
            row = {k: v for k, v in payload.items() if v is not None}
            row["id"] = self._id("part")
            self._parts.append(row)
            return self._copy(row)

    def _inventory_view(self, row: dict) -> dict:
        result = self._copy(row)
        part = next((p for p in self._parts if p["id"] == row["partId"]), None)
        result["partDetail"] = self._copy(part) if part else None
        return result

    def inventory_warning(self) -> list[dict]:
        with self._lock:
            return [self._inventory_view(r) for r in self._inventory if r["currentQuantity"] < r["safetyStock"]]

    def inventory_page(self, current=1, size=10, part_name=None, warehouse_location=None) -> dict:
        with self._lock:
            rows = [self._inventory_view(r) for r in self._inventory]
            if part_name:
                rows = [r for r in rows if self._contains((r.get("partDetail") or {}).get("name"), part_name)]
            if warehouse_location:
                rows = [r for r in rows if self._contains(r.get("warehouseLocation"), warehouse_location)]
            return self._paginate(rows, current, size)

    def get_inventory(self, inventory_id: int) -> dict:
        with self._lock:
            row = next((r for r in self._inventory if r["id"] == inventory_id), None)
            if row is None:
                raise NotFoundError(f"inventory {inventory_id} not found")
            return self._inventory_view(row)

    def inventory_check(self) -> dict:
        with self._lock:
            warnings = [r for r in self._inventory if r["currentQuantity"] < r["safetyStock"]]
            value = sum(
                r["currentQuantity"] * next(p["purchasePrice"] for p in self._parts if p["id"] == r["partId"])
                for r in self._inventory
            )
            return {
                "skuCount": len({r["partId"] for r in self._inventory}),
                "inventoryRecordCount": len(self._inventory),
                "warningCount": len(warnings),
                "totalQuantity": sum(r["currentQuantity"] for r in self._inventory),
                "totalInventoryValue": round(value, 2),
            }

    def inbound(self, part_id: int, quantity: int, warehouse_location: str | None = None) -> dict:
        with self._lock:
            if quantity <= 0:
                raise ValidationError("quantity must be greater than zero")
            if not any(p["id"] == part_id for p in self._parts):
                raise ValidationError(f"part {part_id} not found")
            row = next((r for r in self._inventory if r["partId"] == part_id and (warehouse_location is None or r["warehouseLocation"] == warehouse_location)), None)
            if row is None:
                if warehouse_location is None:
                    warehouse_location = "A-01-01"
                row = {"id": self._id("inventory"), "partId": part_id, "currentQuantity": 0, "safetyStock": 0, "warehouseLocation": warehouse_location}
                self._inventory.append(row)
            row["currentQuantity"] += quantity
            return self._inventory_view(row)

    def outbound(self, part_id: int, quantity: int) -> dict:
        with self._lock:
            if quantity <= 0:
                raise ValidationError("quantity must be greater than zero")
            if not any(p["id"] == part_id for p in self._parts):
                raise ValidationError(f"part {part_id} not found")
            rows = [r for r in self._inventory if r["partId"] == part_id]
            available = sum(r["currentQuantity"] for r in rows)
            if available < quantity:
                raise ConflictError(f"insufficient stock for part {part_id}: available {available}")
            remaining = quantity
            for row in rows:
                amount = min(row["currentQuantity"], remaining)
                row["currentQuantity"] -= amount
                remaining -= amount
                if remaining == 0:
                    return self._inventory_view(row)
            raise AssertionError("validated stock was not fully deducted")

    def _validated_order_details(self, details: list[dict]) -> list[dict]:
        if not details:
            raise ValidationError("orderDetail must contain at least one item")
        result = []
        for detail in details:
            part_id = detail.get("partId")
            if not any(part["id"] == part_id for part in self._parts):
                raise ValidationError(f"part {part_id} not found")
            if detail.get("quantity", 0) < 1 or detail.get("unitPrice", 0) <= 0:
                raise ValidationError("order detail quantity must be >= 1 and unitPrice must be > 0")
            result.append(self._copy(detail))
        return result

    def _order_by_id(self, order_id: int) -> dict:
        row = next((r for r in self._orders if r["id"] == order_id), None)
        if row is None:
            raise NotFoundError(f"order {order_id} not found")
        return row

    @staticmethod
    def _order_total(details: list[dict]) -> float:
        return round(sum(d["quantity"] * d["unitPrice"] for d in details), 2)

    @staticmethod
    def _normalize_order(payload: dict) -> dict:
        result = TestERPStore._copy(payload)
        if not result.get("orderTime"):
            result["orderTime"] = datetime.now().isoformat(timespec="seconds")
        return result

    def create_order(self, payload: dict) -> dict:
        with self._lock:
            if any(r["orderNumber"] == payload["orderNumber"] for r in self._orders):
                raise ConflictError(f"orderNumber {payload['orderNumber']} already exists")
            order = self._normalize_order(payload)
            order["orderDetail"] = self._validated_order_details(order.get("orderDetail", []))
            order["id"] = self._id("order")
            order["totalAmount"] = order.get("totalAmount") if order.get("totalAmount") is not None else self._order_total(order["orderDetail"])
            self._orders.append(order)
            return self._copy(order)

    def update_order(self, order_id: int, payload: dict) -> dict:
        with self._lock:
            existing = self._order_by_id(order_id)
            if any(r["id"] != order_id and r["orderNumber"] == payload["orderNumber"] for r in self._orders):
                raise ConflictError(f"orderNumber {payload['orderNumber']} already exists")
            order = self._normalize_order(payload)
            order["orderDetail"] = self._validated_order_details(order.get("orderDetail", []))
            order["id"] = order_id
            if order.get("totalAmount") is None:
                order["totalAmount"] = self._order_total(order["orderDetail"])
            index = self._orders.index(existing)
            self._orders[index] = order
            return self._copy(order)

    def get_order(self, order_id: int) -> dict:
        with self._lock:
            return self._copy(self._order_by_id(order_id))

    def update_order_status(self, order_id: int, status: int) -> dict:
        with self._lock:
            row = self._order_by_id(order_id)
            row["status"] = status
            return self._copy(row)

    def order_page(self, current=1, size=10, order_number=None, status=None, start_date=None, end_date=None) -> dict:
        with self._lock:
            rows = self._orders
            if order_number:
                rows = [r for r in rows if self._contains(r.get("orderNumber"), order_number)]
            if status is not None:
                rows = [r for r in rows if r.get("status") == status]
            if start_date:
                rows = [r for r in rows if r.get("orderTime", "")[:10] >= start_date]
            if end_date:
                rows = [r for r in rows if r.get("orderTime", "")[:10] <= end_date]
            return self._paginate(rows, current, size)

    def order_search_details(self, part_name=None, start_date=None, end_date=None) -> list[dict]:
        with self._lock:
            result = []
            for order in self._orders:
                if start_date and order.get("orderTime", "")[:10] < start_date:
                    continue
                if end_date and order.get("orderTime", "")[:10] > end_date:
                    continue
                for detail in order["orderDetail"]:
                    part = next((p for p in self._parts if p["id"] == detail["partId"]), None)
                    if part is None or (part_name and not self._contains(part["name"], part_name)):
                        continue
                    supplier = next((s for s in self._suppliers if s["id"] == part.get("supplierId")), None)
                    result.append({
                        "orderId": order["id"], "orderNumber": order["orderNumber"],
                        "orderTime": order["orderTime"], "status": order["status"],
                        **self._copy(detail), "partName": part["name"], "partCode": part["partCode"],
                        "supplierId": part.get("supplierId"),
                        "supplierName": supplier["name"] if supplier else None,
                    })
            return self._copy(result)

    def order_statistics(self, start_date=None, end_date=None) -> dict:
        with self._lock:
            rows = self._orders
            if start_date:
                rows = [r for r in rows if r.get("orderTime", "")[:10] >= start_date]
            if end_date:
                rows = [r for r in rows if r.get("orderTime", "")[:10] <= end_date]
            grouped = {str(status): sum(1 for r in rows if r["status"] == status) for status in range(5)}
            total = round(sum(r.get("totalAmount", 0) for r in rows), 2)
            return {
                "orderCount": len(rows), "totalAmount": total, "statusCounts": grouped,
                "pendingCount": grouped["0"], "approvedCount": grouped["1"],
                "shippingCount": grouped["2"], "receivedCount": grouped["3"],
                "completedCount": grouped["4"],
            }
