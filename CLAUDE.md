# CLAUDE.md

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents

Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills

- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools

- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

### MCP Setup (Windows)

- The `github` and `playwright` servers in `.mcp.json` launch through `npx`, so Node.js must be on PATH. Restart VS Code after installing it or changing environment variables.
- The github server needs the `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable. Never put the token in `.mcp.json` or any committed file.
- If a server fails with `CONNECTION_CLOSED`, run its `npx` command in a terminal to see the real error. A corrupted npx cache (`ERR_MODULE_NOT_FOUND`) is fixed by deleting the matching folder under `%LOCALAPPDATA%\npm-cache\_npx`.

## Stack

- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Quick Start

```bash
# Backend
cd server
uv run python main.py

# Frontend
cd client
npm install && npm run dev

# Backend tests
cd server
uv run pytest ../tests/backend
```

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status) apply to all data via query params
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties

## API Endpoints

- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions
- `GET /api/reports/quarterly`, `/api/reports/monthly-trends` - No filters
- `GET /api/restocking/recommendations?budget=` - Items forecast to run short, within budget
- `GET`/`POST /api/restocking/orders` - Submitted restocking orders (prices and lead time computed server-side)
- `POST /api/purchase-orders`, `GET /api/purchase-orders/{backlog_item_id}` - One PO per backlog item (409 on duplicate). `/api/backlog` returns `purchase_order_id`, which the Dashboard uses to switch "Create PO" to "View PO"

## Common Issues

1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months
6. Purchase orders and restocking orders exist only in memory and are lost on backend restart. Tests that create them must clear `mock_data.purchase_orders` / `mock_data.restocking_orders` with an autouse fixture (see `tests/backend/test_purchase_orders.py`)
7. The client calls `GET /api/tasks` (`api.js`, `App.vue` `loadTasks`) but the backend has no tasks route, so a 404 shows in the console on every page load

## File Locations

- Views: `client/src/views/*.vue`
- Components (modals, `Sidebar.vue`, `FilterBar.vue`): `client/src/components/*.vue`
- Routes: `client/src/main.js` (sidebar links live in `Sidebar.vue`)
- Backend tests: `tests/backend/`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`

## Design System

- Colors: Slate/gray (#0f172a, #64748b, #e2e8f0)
- Status: green/blue/yellow/red
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI

## Code Style

- Always document non-obvious logic changes with comments
