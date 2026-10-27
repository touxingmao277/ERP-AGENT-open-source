"""Deterministic synthetic ERP fixtures."""
from __future__ import annotations

from copy import deepcopy


_SUPPLIERS = [
    {"id": 1, "supplierCode": "SUP-001", "name": "华东精密零部件", "contactPerson": "林工", "phone": "13800001001", "email": "east@example.test", "address": "上海市", "creditRating": "A", "status": 1},
    {"id": 2, "supplierCode": "SUP-002", "name": "安途动力科技", "contactPerson": "周经理", "phone": "13800001002", "email": "antu@example.test", "address": "江苏省苏州市", "creditRating": "B", "status": 1},
    {"id": 3, "supplierCode": "SUP-003", "name": "锐行制动系统", "contactPerson": "陈女士", "phone": "13800001003", "email": "ruixing@example.test", "address": "浙江省宁波市", "creditRating": "C", "status": 1},
    {"id": 4, "supplierCode": "SUP-004", "name": "北辰电气", "contactPerson": "王工", "phone": "13800001004", "email": "beichen@example.test", "address": "北京市", "creditRating": "D", "status": 0},
]

_PARTS = [
    {"id": 101, "partCode": "ENG-001", "name": "单缸发动机总成", "model": "150CC-A", "specification": "150cc 风冷", "unit": "台", "purchasePrice": 1250.0, "suggestedRetailPrice": 1680.0, "stockWarningValue": 4, "supplierId": 1, "category": "发动机系统", "description": "通用单缸发动机"},
    {"id": 102, "partCode": "BRK-001", "name": "前制动片", "model": "BP-09", "specification": "陶瓷复合", "unit": "套", "purchasePrice": 38.5, "suggestedRetailPrice": 69.0, "stockWarningValue": 12, "supplierId": 3, "category": "制动系统", "description": "前轮制动片"},
    {"id": 103, "partCode": "BRK-002", "name": "后制动盘", "model": "BD-12", "specification": "直径220mm", "unit": "件", "purchasePrice": 86.0, "suggestedRetailPrice": 139.0, "stockWarningValue": 8, "supplierId": 3, "category": "制动系统", "description": "不锈钢制动盘"},
    {"id": 104, "partCode": "ELE-001", "name": "点火线圈", "model": "IC-150", "specification": "12V", "unit": "件", "purchasePrice": 52.0, "suggestedRetailPrice": 88.0, "stockWarningValue": 6, "supplierId": 4, "category": "电气系统", "description": "高压点火线圈"},
    {"id": 105, "partCode": "ELE-002", "name": "启动继电器", "model": "SR-12", "specification": "12V 30A", "unit": "件", "purchasePrice": 24.0, "suggestedRetailPrice": 42.0, "stockWarningValue": 8, "supplierId": 4, "category": "电气系统", "description": "电启动继电器"},
    {"id": 106, "partCode": "CON-001", "name": "机油滤芯", "model": "OF-01", "specification": "纸芯过滤", "unit": "个", "purchasePrice": 9.5, "suggestedRetailPrice": 18.0, "stockWarningValue": 20, "supplierId": 2, "category": "耗材", "description": "发动机机油滤芯"},
    {"id": 107, "partCode": "CON-002", "name": "空气滤清器", "model": "AF-15", "specification": "海绵滤材", "unit": "个", "purchasePrice": 18.0, "suggestedRetailPrice": 32.0, "stockWarningValue": 12, "supplierId": 2, "category": "耗材", "description": "可清洗空气滤清器"},
    {"id": 108, "partCode": "CHS-001", "name": "前减震器", "model": "FS-32", "specification": "行程90mm", "unit": "支", "purchasePrice": 310.0, "suggestedRetailPrice": 460.0, "stockWarningValue": 4, "supplierId": 1, "category": "车架系统", "description": "液压前减震器"},
]

_INVENTORY = [
    {"id": 301, "partId": 101, "currentQuantity": 16, "safetyStock": 4, "warehouseLocation": "A-01-01"},
    {"id": 302, "partId": 102, "currentQuantity": 7, "safetyStock": 12, "warehouseLocation": "A-02-01"},
    {"id": 303, "partId": 103, "currentQuantity": 3, "safetyStock": 8, "warehouseLocation": "A-02-02"},
    {"id": 304, "partId": 104, "currentQuantity": 14, "safetyStock": 6, "warehouseLocation": "B-01-01"},
    {"id": 305, "partId": 105, "currentQuantity": 10, "safetyStock": 8, "warehouseLocation": "B-01-02"},
    {"id": 306, "partId": 106, "currentQuantity": 32, "safetyStock": 20, "warehouseLocation": "C-01-01"},
    {"id": 307, "partId": 107, "currentQuantity": 4, "safetyStock": 12, "warehouseLocation": "C-01-02"},
    {"id": 308, "partId": 108, "currentQuantity": 6, "safetyStock": 4, "warehouseLocation": "A-01-02"},
    {"id": 309, "partId": 106, "currentQuantity": 8, "safetyStock": 4, "warehouseLocation": "D-01-01"},
]

_ORDERS = [
    {"id": 501, "orderNumber": "PO-2026-001", "totalAmount": 2500.0, "status": 0, "orderTime": "2026-10-01T09:00:00", "remark": "待审核采购", "orderDetail": [{"partId": 101, "quantity": 2, "unitPrice": 1250.0, "remark": ""}]},
    {"id": 502, "orderNumber": "PO-2026-002", "totalAmount": 385.0, "status": 1, "orderTime": "2026-10-05T10:30:00", "remark": "已审核采购", "orderDetail": [{"partId": 102, "quantity": 10, "unitPrice": 38.5, "remark": ""}]},
    {"id": 503, "orderNumber": "PO-2026-003", "totalAmount": 258.0, "status": 2, "orderTime": "2026-10-10T14:00:00", "remark": "运输中", "orderDetail": [{"partId": 103, "quantity": 3, "unitPrice": 86.0, "remark": ""}]},
    {"id": 504, "orderNumber": "PO-2026-004", "totalAmount": 468.0, "status": 3, "orderTime": "2026-10-18T11:15:00", "remark": "部分收货", "orderDetail": [{"partId": 107, "quantity": 26, "unitPrice": 18.0, "remark": ""}]},
    {"id": 505, "orderNumber": "PO-2026-005", "totalAmount": 310.0, "status": 4, "orderTime": "2026-10-22T16:20:00", "remark": "已完成", "orderDetail": [{"partId": 108, "quantity": 1, "unitPrice": 310.0, "remark": ""}]},
]


def fresh_seed_data() -> dict[str, list[dict]]:
    """Return independent mutable collections based on the fixed fixtures."""
    return deepcopy({
        "suppliers": _SUPPLIERS,
        "parts": _PARTS,
        "inventory": _INVENTORY,
        "orders": _ORDERS,
    })
