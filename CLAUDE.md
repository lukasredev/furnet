# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

FurNet is a teaching app for DevOps workshops. Each participant deploys their own
instance, gives it an "animal" identity by editing code, and connects ("friends")
it to other participants' instances, forming a small decentralized social network.
There is no central server: every instance holds only its own state.

Stack: FastAPI backend (`backend/`), React 19 + Vite + Tailwind CSS v4 frontend
(`frontend/`), and an nginx gateway for Docker Compose.

## Repository Layout

```
furnet/
├── backend/
│   ├── main.py              # FastAPI app, CORS, /health endpoints, mounts router at /api
│   ├── config.py            # Settings (env vars) + AnimalConfig (hardcoded identity)
│   ├── api/models.py        # Pydantic models: Animal, Friend
│   ├── api/routes.py        # All /api endpoints, friend domain allowlist, remote fetching
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile           # python:3.14-slim, uvicorn on :8000, runs as user furnet
├── frontend/
│   ├── src/App.jsx          # Home page (profile, add-friend form, friends) + routes
│   ├── src/components/      # AnimalProfile, FriendList, Monitoring
│   ├── vite.config.js       # Dev server :5173, proxies /api -> localhost:8000
│   ├── nginx.conf           # Serves the built SPA on :8080 + static /health endpoints
│   └── Dockerfile           # Node build stage -> nginx-unprivileged (non-root)
├── tests/                   # Backend pytest suite (conftest.py has the fake network)
├── pytest.ini
├── docker-compose.yml       # backend + frontend + gateway (http://localhost:8080)
├── gateway.conf             # /api, /health, /docs, /openapi.json -> backend; rest -> frontend
└── .github/
    ├── workflows/docker-publish.yml   # Builds and pushes images to GHCR
    ├── workflows/tests.yml            # Runs backend and frontend tests
    └── dependabot.yml                 # Daily updates: pip, npm, actions, docker, compose
```

## Development

Prerequisites: Python 3.12+ (images use 3.14), Node.js 22+ (images use 24).

```bash
# Backend: http://localhost:8000 (API docs at /docs)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
uvicorn main:app --reload

# Frontend: http://localhost:5173 (proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Full stack in Docker: `docker compose up --build`, then open `http://localhost:8080`.

Frontend production build: `npm run build` (and `npm run preview` to serve it).

### Tests and tooling

```bash
# Backend: pytest in the top-level tests/ directory (pytest.ini puts backend/ on the path)
pip install -r backend/requirements-dev.txt   # in the backend venv
pytest                                        # from the repo root

# Frontend: Vitest + Testing Library, tests sit next to the code as *.test.jsx
cd frontend && npm test
```

CI runs both on pushes to `main` and on pull requests (`.github/workflows/tests.yml`).

- `tests/conftest.py` routes DNS lookups and every `httpx.AsyncClient` through a fake
  network (the autouse `network` fixture), so tests never reach real hosts, and it
  resets `friends_db` between tests. It routes by `Host` header because requests to
  hosts outside the allowlist go to a pinned IP. Frontend tests stub `fetch` with
  `mockFetch` from `src/test/fetch.js`.
- Tests read the expected animal from `AnimalConfig` instead of hardcoding it, so they
  keep passing after participants change their animal. Keep it that way.
- `tests/test_security.py` covers SSRF, spoofing, size limits, logs and error details.

No linter, formatter or type checker is configured. Also verify changes by running the
app: exercise endpoints via `http://localhost:8000/docs` or `curl`, and load the frontend.

## Backend

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health`, `/health/live`, `/health/ready` | Health and Kubernetes-style probes |
| GET | `/api/me` | This instance's animal profile (`Animal`) |
| GET | `/api/friends` | List friends |
| POST | `/api/friends` | Add a friend from a `Friend` payload, verified against `https://<dns_name>/api/me` |
| POST | `/api/friends/add` | Add a friend by instance URL: the backend fetches `<url>/api/me` (used by the UI, avoids CORS) |
| POST | `/api/health-check` | Fetch `/api/me` on up to 50 instance URLs concurrently, report up/down and latency (used by the Monitoring page) |

### Behavior worth knowing

- **Animal identity** is the `AnimalConfig` class in `backend/config.py`, hardcoded
  on purpose: participants learn config-as-code and image rebuilds. Do not move it
  to environment variables.
- **Instance ID** is `<host without port>:<animal name, lowercased, spaces -> hyphens>`,
  built by `generate_animal_id()` from `INSTANCE_URL`.
- **Friends live in memory** (`friends_db` in `routes.py`) and are lost on restart.
  Limit is 1000; duplicates and adding yourself are rejected.
- **Friend domain allowlist**: `ALLOWED_FRIEND_DOMAINS` in `routes.py`
  (`vsos.ethz.ch`, `furnet.lukasre.ch` and their subdomains). It is checked against
  the URL being added, before anything is fetched. Anything else gets a 403, including
  `localhost`, so adding friends fails in a purely local setup unless the list is
  extended.
- **Friend identity comes from the contacted host**: `dns_name` is the host that was
  fetched and `unique_id` is built from it and the served name. The `id` and
  `instance_url` a remote reports about itself are not trusted (the `id` is only used
  to catch adding yourself).
- **URL handling**: URLs given to `/api/friends/add` and `/api/health-check` get
  `https://` prepended when no scheme is present and are reduced to scheme, host and
  port (`instance_origin()`); only that origin's `/api/me` is fetched. The frontend
  links friends to `https://<dns_name>`.
- **Health check SSRF guard**: allowlisted hosts are checked directly. Any other host
  is only contacted if all its addresses are public, and the connection is pinned to
  the checked address (Host header and SNI keep the name) so DNS rebinding cannot
  redirect it. Local and Docker-internal URLs therefore show "Blocked".
- **Remote data is untrusted**: profiles are capped at 64 KiB (`MAX_PROFILE_BYTES`),
  friend names at 100 characters, redirects are not followed, and errors returned to
  clients name the exception type only (details go to the log). Log untrusted values
  with `%r` so they cannot forge log lines, and never log remote response bodies.

### Configuration

`Settings` in `config.py` reads environment variables or `backend/.env`
(pydantic-settings):

- `INSTANCE_URL`: the public URL of this instance, used by `/api/me` and the
  instance ID. This is the only setting the code actually reads.
- `API_HOST`, `API_PORT`, `DEBUG`, `CORS_ORIGINS`: defined but not wired up. The
  Docker `CMD` hardcodes host and port, and `main.py` hardcodes CORS to
  `http://localhost:5173`. Browsers reach the API same-origin (Vite proxy or
  gateway) and instance-to-instance calls are server-side, so CORS rarely matters.

## Frontend

- Routes (`react-router-dom`): `/` (profile, add-friend form, friend list) and
  `/monitoring` (polls `/api/health-check` every 5 s for a hardcoded list of
  workshop instances in `Monitoring.jsx`).
- Uses plain `fetch` against relative `/api/...` paths.
- `Monitoring.jsx` refuses more than 50 instances, the backend's per-request limit.
- Tailwind v4 through `@tailwindcss/vite`; there is no `tailwind.config.js`, styles
  start from `@import "tailwindcss"` in `src/index.css`.
- `VITE_COMMIT_HASH` (Docker build arg `COMMIT_HASH`, set by CI) shows the short
  commit hash in the footer.

## Deployment

- `docker compose up --build` runs backend, frontend and the nginx gateway; only the
  gateway is published (port 8080). Compose sets `INSTANCE_URL=http://localhost`.
- CI builds on pushes to `main` and `v*` tags and pushes
  `ghcr.io/<owner>/<repo>/backend` and `.../frontend`, tagged with the branch,
  `<branch>-<sha>`, semver, and `latest`.
- Backend and frontend both expose `/health/live` and `/health/ready` for Kubernetes
  probes, but no Kubernetes manifests live in this repo.
- Changing the animal means rebuilding the backend image.
- All containers run as non-root: the backend as `furnet` (UID 10001), frontend and
  gateway on `nginxinc/nginx-unprivileged` (UID 101), so they listen on 8080, not 80.

## Conventions

- Python: PEP 8, type hints on new function signatures, docstrings on endpoints in
  the style of `routes.py`.
- Commits: conventional commits (`type(scope): description`); branch from `main`
  (`feature/...`, `fix/...`, `chore/...`).
- When a backend change affects what the UI needs, update the React components too.
- Anything that calls a remote instance must handle timeouts, bad responses and
  offline peers; participants' instances are often down or misconfigured.
- `README.md` still describes the original items-only template (mentions
  `tailwind.config.js`, the removed ItemList UI and `/api/items` endpoints, Vite 6)
  and is out of date.
