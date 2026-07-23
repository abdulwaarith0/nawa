# NAWA — Dev Tools & Graphical Interfaces

How to see the running system: the API surface, metrics dashboards, the database, and object storage.

---

## 0. Start everything

```bash
# 1. Core infra (Postgres + MinIO) — usually already running
cd D:/Abdulwaarith/Desktop/nawa
docker compose up -d

# 2. The API server (needed for /docs and for the metrics dashboards to have data)
cd services/api
ENVIRONMENT=development JWT_SECRET="change-me-in-development-only" \
  uv run uvicorn nawa_api.main:app --port 8000 --reload

# 3. The dev GUIs (pgAdmin + Prometheus + Grafana)
cd D:/Abdulwaarith/Desktop/nawa
docker compose -f docker-compose.tools.yml up -d
```

Stop the GUIs with `docker compose -f docker-compose.tools.yml down` (its own isolated
`nawa-tools` project — it can never touch the core Postgres/MinIO).

---

## 1. The API — Swagger UI & ReDoc  ⭐ start here

FastAPI auto-generates interactive docs for **every** endpoint. This is where you see and
*try* auth, IAM, rate limiting, CORS, the envelope — all of it.

| URL | What it is |
|---|---|
| http://localhost:8000/docs | **Swagger UI** — interactive: click "Try it out", send real requests, see the `{code,message,data}` envelope and response headers (incl. `X-RateLimit-*`, `X-Request-Id`) |
| http://localhost:8000/redoc | **ReDoc** — clean, read-only API reference |
| http://localhost:8000/openapi.json | Raw OpenAPI schema (this feeds the TS codegen in the next slice) |

**How to try an authenticated call in Swagger:**
1. `POST /api/v1/auth/login` with `{"identifier":"admin@nawa.local","password":"password"}`
   and header `X-Client: web`, `X-Device-Id: dev1` → copy the `access_token` from the response.
2. Click the green **Authorize** button (top right), paste `Bearer <access_token>`.
3. Now call gated endpoints like `GET /api/v1/iam/policies`.

**Seeing rate limiting:** hammer `POST /api/v1/auth/login` ~11 times → the 11th returns
**429** with a `Retry-After` header. Every response carries `X-RateLimit-Limit/Remaining/Reset`.

**Seeing CORS:** CORS is a browser-enforced response-header behavior (allowed origin =
`http://localhost:3000`, the web app). You see it in browser DevTools → Network → response
headers (`access-control-allow-origin`), not as a separate UI.

---

## 2. Metrics — Prometheus & Grafana

The API exposes Prometheus metrics at http://localhost:8000/api/v1/metrics (plain text).
Two custom histograms: `http_request_duration_seconds` and `database_request_duration_seconds`.

| URL | Login | What it is |
|---|---|---|
| http://localhost:9090 | — | **Prometheus** — query metrics directly (try `sum(rate(http_request_duration_seconds_count[1m])) by (route)`); check **Status → Targets** to confirm it's scraping the API |
| http://localhost:3001 | `admin` / `nawa` (or anonymous view) | **Grafana** — open dashboard **"NAWA API Overview"** (folder NAWA): request rate by route, p95 latency, responses by status code, DB query latency |

Grafana refreshes every 5s. Generate traffic (use Swagger, or `curl` the API) and watch the
panels move. Prometheus + Grafana come pre-provisioned — no manual datasource/dashboard setup.

---

## 3. Postgres — pgAdmin

| URL | Login |
|---|---|
| http://localhost:5050 | email `admin@nawa.dev` / password `nawa` |

The **NAWA Dev** server is pre-registered under the "NAWA" group. Expand it → enter the DB
password **`nawa`** once when prompted → browse:
`Servers → NAWA Dev → Databases → nawa_dev → Schemas → public → Tables`.
Right-click any table → **View/Edit Data → All Rows** to see the seeded data (200 applications,
50 founder profiles, 6 programs, etc.). Or use **Query Tool** to run SQL.

**Prefer a desktop pgAdmin / DBeaver / TablePlus?** Connect with:
`host localhost · port 5433 · database nawa_dev · user nawa · password nawa`.

---

## 4. Object storage — MinIO

| URL | Login |
|---|---|
| http://localhost:9001 | `nawa` / `nawa12345` |

The S3-compatible console. Buckets/uploads land here in later slices (intake documents, report
exports). Empty for now.

---

## 5. Logs

Structured logs print to the API server's console (pretty format in development, one JSON line
per event in production). Each request emits exactly one access line with `request_id`, method,
path, status, `duration_ms`, and ip. There's no separate log GUI in dev — the console is it.
(A log-aggregation UI like Loki/Grafana could be added later if wanted.)

---

## Quick reference — all local URLs

| Service | URL | Login |
|---|---|---|
| API — Swagger | http://localhost:8000/docs | authorize with a bearer token |
| API — ReDoc | http://localhost:8000/redoc | — |
| API — metrics (raw) | http://localhost:8000/api/v1/metrics | — |
| Grafana (dashboards) | http://localhost:3001 | admin / nawa |
| Prometheus | http://localhost:9090 | — |
| pgAdmin | http://localhost:5050 | admin@nawa.dev / nawa |
| MinIO console | http://localhost:9001 | nawa / nawa12345 |
| Web app (Slice 4 frontend, not built yet) | http://localhost:3000 | — |
