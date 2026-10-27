# Test ERP Design

## Goal

Provide a local, deterministic ERP HTTP service that implements every REST
contract consumed by the project's 23 MCP tools. It enables end-to-end testing
of the FastAPI Agent, MCP gateway, and ERP business workflows without a Java
ERP installation.

## Scope

- Create a standalone FastAPI service under `evals/test_erp/`.
- Bind only to `127.0.0.1:8081` by default.
- Cover all supplier, part, order, and inventory routes exposed by
  `src/mcp_server/tools/`.
- Keep state in memory, seeded deterministically when the process starts.
- Test the service at HTTP, MCP, and selected Agent workflow layers.

The service is a development and automated-test dependency. It must not be
used as a production ERP substitute, and it must not write to MongoDB or any
external system.

## Existing Contract

The test service is compatible with `ERPHttpClient` in
`src/mcp_server/http_base.py`. Successful responses use:

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

Page responses put the following object in `data`:

```json
{
  "records": [],
  "total": 0,
  "current": 1,
  "size": 10,
  "pages": 0
}
```

Missing resources return HTTP 404 with the same envelope, using `code: 404`.
Invalid requests return HTTP 400 with `code: 400`. Business rejections such as
insufficient stock use HTTP 409 with `code: 409`.

## HTTP Surface

### Suppliers

| MCP tool | Method and path | Behavior |
| --- | --- | --- |
| `supplier_query` | `GET /api/suppliers/search?name=` | Case-insensitive name search. |
| `supplier_page` | `GET /api/suppliers/page` | Filter by name, `status`, `creditRating`; paginate. |
| `supplier_get` | `GET /api/suppliers/get/{id}` | Return one supplier. |
| `supplier_create` | `POST /api/suppliers/create` | Require unique `supplierCode` and a name. |
| `supplier_update_status` | `PATCH /api/suppliers/update-status/{id}?status=` | Allow status `0` or `1`. |

### Parts

| MCP tool | Method and path | Behavior |
| --- | --- | --- |
| `part_query` | `GET /api/parts/get/{id}` | Return one part. |
| `part_search` | `GET /api/parts/search?name=` | Case-insensitive name search. |
| `part_by_supplier` | `GET /api/parts/supplier/{supplier_id}` | Return parts by supplier. |
| `part_page` | `GET /api/parts/page` | Filter by name, category, `supplierId`; paginate. |
| `part_create` | `POST /api/parts/create` | Require unique `partCode`, name, and non-negative purchase price. |

### Orders

| MCP tool | Method and path | Behavior |
| --- | --- | --- |
| `order_create` | `POST /api/orders/create` | Validate a unique `orderNumber`, part references, positive quantities and prices; derive `totalAmount` when omitted. |
| `order_update` | `PUT /api/orders/update/{id}` | Apply the same detail validation before replacing the order. |
| `order_page` | `GET /api/orders/page` | Filter by order number, status, and inclusive date range; paginate. |
| `order_get` | `GET /api/orders/get/{id}` | Return an order with `orderDetail`. |
| `order_search_details` | `GET /api/orders/search-details` | Return flattened details with associated part and supplier data. |
| `order_statistics` | `GET /api/orders/statistics` | Return counts, total amount, and counts grouped by status. |
| `order_update_status` | `PATCH /api/orders/update-status/{id}?status=` | Permit only status values `0` through `4`. |

### Inventory

| MCP tool | Method and path | Behavior |
| --- | --- | --- |
| `inventory_warning` | `GET /api/inventory/warning` | Return rows where `currentQuantity < safetyStock`. |
| `inventory_page` | `GET /api/inventory/page` | Filter by part name and warehouse; paginate. |
| `inventory_check` | `GET /api/inventory/check` | Return SKU count, warning count, total quantity, and total inventory value. |
| `inventory_inbound` | `POST /api/inventory/inbound` | Require a known part and positive quantity; add to stock. |
| `inventory_outbound` | `POST /api/inventory/outbound` | Require a known part, positive quantity, and sufficient stock; subtract from stock. |
| `inventory_get` | `GET /api/inventory/get/{id}` | Return one inventory row with its `partDetail`. |

## Components

```text
evals/test_erp/
  __init__.py          Package marker
  app.py               FastAPI factory, health route, router registration
  schemas.py           Pydantic request models and response-envelope helpers
  store.py             Thread-safe in-memory repository and business methods
  seed_data.py         Immutable seed fixtures and fresh-copy factory
  routes/
    suppliers.py       Supplier HTTP routes
    parts.py           Part HTTP routes
    orders.py          Order HTTP routes
    inventory.py       Inventory HTTP routes
  __main__.py          `python -m evals.test_erp` startup entry point
src/test/
  test_test_erp.py     HTTP contract and state-transition tests
  test_test_erp_mcp.py MCP-to-test-ERP integration tests
```

`store.py` owns all mutable collections and ID allocation. Route modules only
parse request data, invoke one store method, and map expected domain errors to
the documented response envelope. This keeps REST mechanics separate from
business-state behavior and lets unit tests initialize fresh stores cheaply.

## Seed Data

Seed fixtures include at least four suppliers covering credit ratings A through
D and active/inactive statuses, eight parts across engine, braking, electrical,
and consumable categories, inventory in two warehouse locations, at least two
low-stock rows, and orders in statuses 0 through 4. Every inventory row refers
to an existing part and every seeded order detail refers to an existing part.

Records are copied from immutable seed data for each `TestERPStore` instance;
tests never share state. `POST /api/test/reset` is deliberately excluded so a
running endpoint cannot mutate data outside normal ERP operations. Restarting
the local process resets it to the seed state.

## Runtime Isolation

The service starts with:

```powershell
python -m evals.test_erp
```

Its default Uvicorn configuration is host `127.0.0.1`, port `8081`. It does not
inspect or alter `.env`, start Docker, terminate existing listeners, or modify
MCP configuration. Uvicorn fails normally if the port is already occupied;
the operator must stop the Java ERP before choosing this test service.

For MCP integration, the process launching MCP supplies:

```text
ERP_BASE_URL=http://127.0.0.1:8081
```

The existing `.env` remains unchanged. Because `server_config.py` reads this
setting on MCP startup, MCP is restarted after the environment selection.

## Verification

1. HTTP contract tests cover all 23 routes, including page metadata, filters,
   response envelopes, missing IDs, validation errors, and write-after-read
   state visibility.
2. Inventory tests verify warning thresholds, inbound changes, successful
   outbound changes, and no mutation after an insufficient-stock rejection.
3. Order tests verify detail validation, computed totals, details search,
   date/status filtering, statistics, and state transitions.
4. MCP integration tests point an `ERPHttpClient` at a test-server fixture,
   register all four MCP tool modules, invoke all 23 tools, and validate the
   returned JSON envelope.
5. A manual smoke sequence starts the test ERP on 8081, restarts MCP with the
   local `ERP_BASE_URL`, then uses FastAPI Agent requests for a part lookup,
   inventory warning, and both order approval decisions. The approval path
   creates exactly one order; rejection creates none.

## Non-Goals

- No persistence across restarts.
- No authentication, authorization, users, tenancy, or audit policy.
- No simulation of Java framework behavior, database transactions, performance,
  distributed concurrency, or production data volumes.
- No automatic port takeover, `.env` edits, or real ERP process control.
