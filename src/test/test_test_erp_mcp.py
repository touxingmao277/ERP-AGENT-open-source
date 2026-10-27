"""Exercise the existing MCP tools over HTTP against the ERP test service."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from langchain_core.tools import StructuredTool

from evals.test_erp.app import create_app
from src.mcp_server.tools import inventory_tools, order_tools, parts_tools, suppliers_tools
from src.mcp_server.http_base import erp_client


class ToolRegistry:
    def __init__(self):
        self.tools = []

    def tool(self):
        def register(fn):
            self.tools.append(StructuredTool.from_function(
                coroutine=fn, name=fn.__name__, description=fn.__doc__
            ))
            return fn
        return register


EXPECTED_TOOLS = {
    "supplier_query", "supplier_page", "supplier_get", "supplier_create",
    "supplier_update_status", "part_query", "part_search", "part_by_supplier",
    "part_page", "part_create", "order_create", "order_update", "order_page",
    "order_get", "order_search_details", "order_statistics", "order_update_status",
    "inventory_warning", "inventory_page", "inventory_check", "inventory_inbound",
    "inventory_outbound", "inventory_get",
}


class TestERPMCPIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app()
        self.http = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.ASGITransport(app=self.app),
        )
        self.previous_http = getattr(erp_client, "_client", None)
        erp_client._client = self.http
        registry = ToolRegistry()
        for module, register in (
            (suppliers_tools, suppliers_tools.register_supplier_tools),
            (parts_tools, parts_tools.register_parts_tools),
            (order_tools, order_tools.register_order_tools),
            (inventory_tools, inventory_tools.register_inventory_tools),
        ):
            with patch.object(module, "erp_client", erp_client):
                register(registry)
        self.tools = {tool.name: tool for tool in registry.tools}

    async def asyncTearDown(self):
        await self.http.aclose()
        erp_client._client = self.previous_http

    async def invoke(self, name: str, args: dict | None = None) -> dict:
        raw = await self.tools[name].ainvoke(args or {})
        return json.loads(raw)

    async def test_all_23_tools_follow_the_http_contract_and_state_changes(self):
        self.assertEqual(set(self.tools), EXPECTED_TOOLS)

        calls = [
            ("supplier_query", {"name": "华东"}),
            ("supplier_page", {"current": 1, "size": 2, "credit_rating": "A"}),
            ("supplier_get", {"id": 1}),
            ("supplier_create", {"supplier_code": "MCP-SUP-1", "name": "MCP测试供应商"}),
            ("supplier_update_status", {"id": 1, "status": 0}),
            ("part_query", {"id": 101}),
            ("part_search", {"name": "发动机"}),
            ("part_by_supplier", {"supplier_id": 1}),
            ("part_page", {"current": 1, "size": 2, "supplier_id": 1}),
            ("part_create", {"part_code": "MCP-PART-1", "name": "MCP新零件", "purchase_price": 11.5, "supplier_id": 1}),
            ("order_create", {"order_data": json.dumps({"orderNumber": "MCP-ORDER-1", "orderDetail": [{"partId": 101, "quantity": 2, "unitPrice": 5.0}]})}),
            ("order_update", {"id": 501, "order_data": json.dumps({"orderNumber": "PO-2026-001", "status": 1, "orderDetail": [{"partId": 101, "quantity": 1, "unitPrice": 1250.0}]})}),
            ("order_page", {"current": 1, "size": 2, "status": 1}),
            ("order_get", {"id": 501}),
            ("order_search_details", {"part_name": "发动机"}),
            ("order_statistics", {}),
            ("order_update_status", {"id": 501, "status": 2}),
            ("inventory_warning", {}),
            ("inventory_page", {"current": 1, "size": 3, "warehouse_location": "A-"}),
            ("inventory_check", {}),
            ("inventory_inbound", {"part_id": 101, "quantity": 2, "warehouse_location": "A-01-01"}),
            ("inventory_outbound", {"part_id": 101, "quantity": 1}),
            ("inventory_get", {"id": 301}),
        ]
        results = {}
        for name, args in calls:
            with self.subTest(tool=name):
                result = await self.invoke(name, args)
                self.assertEqual(result["code"], 200, result)
                self.assertIn("data", result)
                results[name] = result["data"]

        self.assertEqual(results["supplier_get"]["id"], 1)
        self.assertEqual(results["part_query"]["id"], 101)
        self.assertEqual(results["order_get"]["orderNumber"], "PO-2026-001")
        self.assertEqual(results["inventory_get"]["currentQuantity"], 17)

    async def test_inventory_conflict_is_not_reported_as_success(self):
        result = await self.invoke("inventory_outbound", {"part_id": 101, "quantity": 99999})
        self.assertEqual(result["code"], 409)
        self.assertEqual(result["data"]["code"], 409)


if __name__ == "__main__":
    unittest.main()
