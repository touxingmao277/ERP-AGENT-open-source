"""Contract tests for the local ERP test double.

Each test names an externally observable behavior. They must keep passing
against the HTTP service regardless of its in-memory implementation details.
"""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from evals.test_erp.app import create_app


class TestERPHTTPContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def assert_success(self, response, expected_status: int = 200) -> dict:
        self.assertEqual(response.status_code, expected_status, response.text)
        body = response.json()
        self.assertEqual(body["code"], expected_status)
        self.assertIn("message", body)
        self.assertIn("data", body)
        return body["data"]

    def first_part(self) -> dict:
        page = self.assert_success(self.client.get("/api/parts/page"))["records"]
        self.assertTrue(page)
        return page[0]

    def test_registers_all_23_mcp_backing_routes(self) -> None:
        expected = {
            ("GET", "/api/suppliers/search"),
            ("GET", "/api/suppliers/page"),
            ("GET", "/api/suppliers/get/{id}"),
            ("POST", "/api/suppliers/create"),
            ("PATCH", "/api/suppliers/update-status/{id}"),
            ("GET", "/api/parts/get/{id}"),
            ("GET", "/api/parts/search"),
            ("GET", "/api/parts/supplier/{supplier_id}"),
            ("GET", "/api/parts/page"),
            ("POST", "/api/parts/create"),
            ("POST", "/api/orders/create"),
            ("PUT", "/api/orders/update/{id}"),
            ("GET", "/api/orders/page"),
            ("GET", "/api/orders/get/{id}"),
            ("GET", "/api/orders/search-details"),
            ("GET", "/api/orders/statistics"),
            ("PATCH", "/api/orders/update-status/{id}"),
            ("GET", "/api/inventory/warning"),
            ("GET", "/api/inventory/page"),
            ("GET", "/api/inventory/check"),
            ("POST", "/api/inventory/inbound"),
            ("POST", "/api/inventory/outbound"),
            ("GET", "/api/inventory/get/{id}"),
        }
        registered = {
            (method.upper(), path)
            for path, operations in self.client.app.openapi()["paths"].items()
            for method in operations
            if method.lower() not in {"head", "options"}
        }
        self.assertEqual(len(expected), 23)
        api_routes = {(method, path) for method, path in registered if path.startswith("/api/")}
        self.assertEqual(api_routes, expected)

    def test_supplier_and_part_writes_are_visible_to_queries(self) -> None:
        supplier = self.assert_success(self.client.post("/api/suppliers/create", json={
            "supplierCode": "TEST-SUP-01",
            "name": "测试供应商",
            "creditRating": "B",
            "status": 1,
        }))
        self.assertEqual(supplier["name"], "测试供应商")
        self.assert_success(self.client.patch(
            f"/api/suppliers/update-status/{supplier['id']}", params={"status": 0}
        ))
        inactive = self.assert_success(self.client.get("/api/suppliers/page", params={"status": 0}))
        self.assertIn(supplier["id"], {row["id"] for row in inactive["records"]})

        part = self.assert_success(self.client.post("/api/parts/create", json={
            "partCode": "TEST-PART-01",
            "name": "测试滤芯",
            "purchasePrice": 12.5,
            "supplierId": supplier["id"],
            "category": "耗材",
            "unit": "件",
            "stockWarningValue": 3,
        }))
        found = self.assert_success(self.client.get("/api/parts/search", params={"name": "滤芯"}))
        self.assertIn(part["id"], {row["id"] for row in found})
        supplier_parts = self.assert_success(self.client.get(f"/api/parts/supplier/{supplier['id']}"))
        self.assertIn(part["id"], {row["id"] for row in supplier_parts})
        filtered = self.assert_success(self.client.get("/api/parts/page", params={"category": "耗材"}))
        self.assertIn(part["id"], {row["id"] for row in filtered["records"]})

    def test_order_lifecycle_exposes_details_statistics_and_validation(self) -> None:
        part = self.first_part()
        created = self.assert_success(self.client.post("/api/orders/create", json={
            "orderNumber": "TEST-ORDER-01",
            "status": 0,
            "remark": "contract test",
            "orderDetail": [{"partId": part["id"], "quantity": 3, "unitPrice": 7.5}],
        }))
        self.assertEqual(created["totalAmount"], 22.5)
        fetched = self.assert_success(self.client.get(f"/api/orders/get/{created['id']}"))
        self.assertEqual(fetched["orderDetail"][0]["partId"], part["id"])
        paged = self.assert_success(self.client.get("/api/orders/page", params={"orderNumber": "TEST-ORDER"}))
        self.assertEqual([row["id"] for row in paged["records"]], [created["id"]])
        details = self.assert_success(self.client.get("/api/orders/search-details", params={"partName": part["name"]}))
        self.assertTrue(any(row["orderId"] == created["id"] for row in details))
        self.assert_success(self.client.patch(
            f"/api/orders/update-status/{created['id']}", params={"status": 1}
        ))
        updated = self.assert_success(self.client.put(f"/api/orders/update/{created['id']}", json={
            "orderNumber": "TEST-ORDER-01",
            "status": 1,
            "orderDetail": [{"partId": part["id"], "quantity": 4, "unitPrice": 7.5}],
        }))
        self.assertEqual(updated["totalAmount"], 30.0)
        statistics = self.assert_success(self.client.get("/api/orders/statistics"))
        self.assertGreaterEqual(statistics["orderCount"], 1)
        invalid = self.client.post("/api/orders/create", json={
            "orderNumber": "BAD-ORDER", "orderDetail": [{"partId": 999999, "quantity": 1, "unitPrice": 1}]
        })
        self.assert_success(invalid, 400)

    def test_inventory_movements_preserve_stock_on_conflict(self) -> None:
        warnings = self.assert_success(self.client.get("/api/inventory/warning"))
        self.assertTrue(warnings)
        inventory_id = warnings[0]["id"]
        before = self.assert_success(self.client.get(f"/api/inventory/get/{inventory_id}"))
        self.assert_success(self.client.post("/api/inventory/inbound", params={
            "partId": before["partId"], "quantity": 5, "warehouseLocation": before["warehouseLocation"]
        }))
        increased = self.assert_success(self.client.get(f"/api/inventory/get/{inventory_id}"))
        self.assertEqual(increased["currentQuantity"], before["currentQuantity"] + 5)
        self.assert_success(self.client.post("/api/inventory/outbound", params={
            "partId": before["partId"], "quantity": 2
        }))
        decreased = self.assert_success(self.client.get(f"/api/inventory/get/{inventory_id}"))
        self.assertEqual(decreased["currentQuantity"], before["currentQuantity"] + 3)
        rejected = self.client.post("/api/inventory/outbound", params={
            "partId": before["partId"], "quantity": 100000
        })
        self.assert_success(rejected, 409)
        unchanged = self.assert_success(self.client.get(f"/api/inventory/get/{inventory_id}"))
        self.assertEqual(unchanged["currentQuantity"], decreased["currentQuantity"])
        self.assert_success(self.client.get("/api/inventory/page", params={"partName": before["partDetail"]["name"]}))
        summary = self.assert_success(self.client.get("/api/inventory/check"))
        self.assertGreaterEqual(summary["skuCount"], 1)

    def test_missing_resources_return_enveloped_404(self) -> None:
        response = self.client.get("/api/parts/get/999999")
        self.assert_success(response, 404)
        self.assertIsNone(response.json()["data"])


if __name__ == "__main__":
    unittest.main()
