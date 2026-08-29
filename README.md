# NAWA — The AI Operating System for Innovation Ecosystems

> *Nawa* means "nucleus / seed" in Arabic — the core from which everything grows.

NAWA is one AI platform running the shared lifecycle behind every innovation program
(accelerators, incubators, research-to-startup tracks, startup-in-residence, and internship
programs): intelligent **intake** screening, cohort **journey** tracking, a
**community** hub, and automated **reporting** — all built on one data spine, the *Founder Profile*.

**Stack:** Next.js 15 (web) · FastAPI + Python 3.12 (API) · PostgreSQL 16 + pgvector · Redis ·
MinIO (S3) · a provider-agnostic LLM gateway (Claude default). Arabic-first, RTL, bilingual AR/EN.

---

## 🚀 Quick start for teammates (Docker only — no Python, no Node needed)

If you just want to **run the backend and click around the API**, you only need
[Docker Desktop](https://www.docker.com/products/docker-desktop/). Nothing else.

```bash
git clone <this-repo-url> nawa
cd nawa
docker compose -f docker-compose.full.yml up --build
```

This builds and starts **everything**: PostgreSQL, Redis, MinIO, and the API. On first boot it
runs the database migrations and seeds a realistic demo dataset (200 applications, 50 founder
profiles, 6 programs, etc.) — that takes ~30–60s, so wait for the log line `Starting API on :8000`.

Then open:

| URL | What it is | Login |
|---|---|---|
| **http://localhost:8000/docs** | **Swagger UI** — try every endpoint interactively | (see below) |
| http://localhost:8000/redoc | Clean API reference | — |
| http://localhost:8000/healthz | Liveness check | — |
| http://localhost:9001 | MinIO console (object storage) | `nawa` / `nawa12345` |

**Try a logged-in request in Swagger:**
1. `POST /api/v1/auth/login` with body `{"identifier":"admin@nawa.local","password":"password"}`
   and headers `X-Client: web`, `X-Device-Id: dev1` → copy the `access_token` from the response.
2. Click the green **Authorize** button (top-right) and paste `Bearer <access_token>`.
3. Now call gated endpoints like `GET /api/v1/iam/policies`.

**Seeded logins** (all password `password`): `admin@nawa.local`, `manager@nawa.local`,
`reviewer@nawa.local`, `founder@nawa.local`, `mentor@nawa.local`, `moderator@nawa.local`,
`member@nawa.local`.

Stop everything with `Ctrl-C`, then `docker compose -f docker-compose.full.yml down`
(add `-v` to also wipe the database volume).

> **Note on ports:** the full stack uses Postgres `5433`, MinIO `9000/9001`, API `8000`, and its
> own Redis on `6380`. If any are taken on your machine, edit `docker-compose.full.yml`.

---

## 🖥️ Running the web frontend

The web app (Next.js) currently needs Node. With the API already running (either via Docker above
or locally below):

```bash
# one-time: install Node 20+ and pnpm (npm i -g pnpm)
pnpm install
pnpm --filter web dev
```

Open **http://localhost:3000** (landing) and **http://localhost:3000/styleguide** (the design
system — click the language toggle to flip AR ⇄ EN and watch it mirror to RTL). The web app proxies
`/api/*` to the API, so keep the API running.

---

## 🛠️ Full local development setup

You do **not** need Python pre-installed — **`uv` downloads and manages Python 3.12 for you.**

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Postgres/Redis/MinIO)
- [uv](https://docs.astral.sh/uv/) — the Python toolchain manager. Install it:
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`
  - `uv` will install Python 3.12 automatically the first time you run a command — **no separate
    Python install required.**
- [Node.js 20+](https://nodejs.org/) and pnpm (`npm i -g pnpm`) — for the web app + codegen.

### 1. Start the infrastructure

```bash
docker compose up -d          # Postgres (:5433) + MinIO (:9000)
```

Redis: the canonical `docker-compose.yml` reuses a shared host Redis on `:6379`. If you don't have
one running, start one: `docker run -d --name redis -p 6379:6379 redis:7-alpine`.

### 2. Set up env + database

```bash
cd services/api
# env/development.env already has working dev defaults (gitignored)
uv run alembic upgrade head       # create the schema (uv installs Python 3.12 on first run)
uv run python -m nawa_api.seed    # seed the demo dataset (~30s)
```

### 3. Run the API

```bash
cd services/api
ENVIRONMENT=development JWT_SECRET="change-me-in-development-only" \
  uv run uvicorn nawa_api.main:app --port 8000 --reload
```

### 4. Run the web app

```bash
pnpm install
pnpm --filter web dev             # http://localhost:3000
```

---

## ✅ Tests

```bash
# API (pytest, against a throwaway test database it creates + drops itself)
cd services/api && uv run pytest -q

# Web + packages (vitest)
pnpm --filter web test
pnpm --filter @nawa/api-client test

# Type-check + lint the JS workspace
pnpm ts.check
pnpm lint
```

## 🔁 Regenerating the API↔TS contracts

The TypeScript types and client are generated from the API's OpenAPI schema — never hand-edited:

```bash
pnpm contracts:generate           # exports openapi.json + generates api.ts / iam.ts
```

---

## 📊 Optional dev GUIs (pgAdmin, Prometheus, Grafana)

```bash
docker compose -f docker-compose.tools.yml up -d
```

- **pgAdmin** (browse the database): http://localhost:5050 — `admin@nawa.dev` / `nawa`
  (the "NAWA Dev" server is pre-registered; DB password is `nawa`)
- **Grafana** (metrics dashboards): http://localhost:3001 — `admin` / `nawa`
- **Prometheus**: http://localhost:9090

See [`DEV-TOOLS.md`](./DEV-TOOLS.md) for the full guide, and
[`NAWA-TECH-STACK.md`](./NAWA-TECH-STACK.md) for the complete stack + versions.

---

## 📁 Repository layout

```
nawa/
├─ apps/web/            Next.js frontend (pure UI, HTTP only)
├─ services/api/        FastAPI service — owns ALL data access (Postgres + Redis + S3)
├─ packages/contracts/  TS types + zod schemas GENERATED from the API's OpenAPI spec
├─ packages/api-client/ typed TS client over the response envelope
├─ env/                 unified env source (only example.env is committed)
├─ docker-compose.yml       Postgres + MinIO (reuses shared host Redis)
├─ docker-compose.full.yml  self-contained stack for teammates (incl. its own Redis + API)
└─ docker-compose.tools.yml pgAdmin + Prometheus + Grafana (dev-only)
```

## 🔒 Notes

- This is a **development** setup. All credentials in the compose files and `env/example.env` are
  **dev-only placeholders** (e.g. Postgres `nawa`/`nawa`). Never use them in production.
- Real secrets live in `env/development.env` (gitignored) and are never committed.
- The AI provider defaults to a deterministic **mock** offline — no API keys needed to run or test.
