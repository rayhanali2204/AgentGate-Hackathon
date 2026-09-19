# AgentGate

**Zero-Trust Security for Autonomous AI Agents**

Every AI tool call is intercepted, evaluated and audited before execution. Milestones 1–4 provide the Python engine, REST API, deterministic agent simulations, and React dashboard. Milestone 5 packages the application for a single-container, same-origin production setup.

## Local setup

Requires Python 3.12+ and Node.js 22.12+ with npm.

Install backend dependencies from the repository root:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e './backend[test]'
```

Terminal 1:

```sh
cd backend
.venv/bin/python -m uvicorn app.main:app --reload
```

Terminal 2:

```sh
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Backend documentation: http://127.0.0.1:8000/docs.

During Vite development the frontend defaults to `http://127.0.0.1:8000`. Production builds default to same-origin API paths. To override the API address, create `frontend/.env.local` containing:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

An explicitly empty `VITE_API_BASE_URL` selects same-origin requests even in development. Restart Vite after changing environment settings. This setting is public build-time configuration, not a place for secrets. The backend allows the exact browser origin `http://localhost:5173`; use that URL, not `http://127.0.0.1:5173`. Vite uses a strict port so it cannot silently switch to an origin rejected by CORS.

## Run the demo

1. Open the dashboard and confirm **API connected**.
2. Choose **Prompt injection** and click **Run Attack Simulation**. The timeline separates the trusted user request from an untrusted retrieved document. The manipulated agent proposes reading 5,000 sensitive customer records for an external destination.
3. AgentGate returns **BLOCK / 80 / CRITICAL**. Both sensitive-data policies trigger. **ATTACK BLOCKED — Protected tool executed: NO** confirms the fake database was never invoked.
4. Select **View audit event** to inspect the corresponding event in the existing audit log.
5. Run **Normal workflow**: `orders.lookup` and `email.send` are both ALLOW and execute as simulations. Outcome: **WORKFLOW COMPLETED**.
6. Run **Human approval**: the allowlisted delete receives REQUIRE_APPROVAL and does not execute. Outcome: **HUMAN APPROVAL REQUIRED**. This milestone does not implement an approve/resume button.

The agent and tools are deterministic simulations, not a real LLM or production integrations. No real email or customer data is used. **AgentGate does not need to perfectly detect malicious text; it controls the actions an agent may perform.** Risk explains danger; deterministic policies authorize actions. See [backend/README.md](backend/README.md) for the full threat model and API behavior.

## Dashboard architecture

```text
frontend/
├── index.html
├── package.json / package-lock.json
├── tsconfig.json / vite.config.ts
└── src/
    ├── api/client.ts          # centralized fetch, timeout and error handling
    ├── types/index.ts         # API contract types
    ├── lib/events.ts          # API-derived metrics and combined filters
    ├── components/            # navigation, metrics, scenarios, timeline,
    │                         # architecture, audit feed and event inspector
    ├── test/                  # API, metrics, filtering and dashboard tests
    ├── App.tsx / main.tsx
    └── styles.css             # responsive, accessible dark SOC interface
```

React, TypeScript, Vite, and Lucide icons; no UI framework, router, or diagram library. Python core and existing tests are unchanged.

The API client uses `GET /api/health`, `GET /api/scenarios`, `POST /api/scenarios/{id}/run`, and `GET /api/events`. The event inspector reads the complete event returned by the events endpoint. Metrics are derived from the full fetched audit log: observed unique agents, evaluated actions, blocks, and approval decisions. They do not imply an inventory of protected agents or count actual tool executions.

Decision, severity, and agent filters combine on the client. The audit table shows six events per page. Scenario runs refresh the log without a page reload; manual refresh also checks API health. There is no background polling. Failed refreshes preserve and clearly label stale data. Empty logs are empty, never filled with demo statistics or invented events. Scenario buttons are disabled while a run is pending, and POST requests are never automatically retried. If a request times out, inspect/refresh the log before running again; the server may have completed it.

The event store remains process-local and in-memory. Restarting the backend clears the audit log. Audit events record authorization; the scenario timeline separately reports actual simulated tool execution. Development UI and tools are not a production authentication or security boundary.

## Verification

From the repository root:

```sh
backend/.venv/bin/python -m pytest -q backend/tests
```

From `frontend/`:

```sh
npm run typecheck
npm test
npm run build
```

`npm run preview` previews static frontend files only. Production builds use same-origin API requests, so use FastAPI static hosting or Docker below to verify the complete production application.

Accessibility includes text/icon decision labels, semantic landmarks, labeled filters, keyboard-accessible event selection, visible focus states, error/loading announcements, and reduced-motion support. Typography uses system fonts with no external font requests.

## Production: one same-origin container

```text
Browser → http://localhost:8000
                     ↓
                  FastAPI
                  ├── /api/*       Existing AgentGate JSON API
                  ├── /assets/*    Compiled React assets
                  └── /*           React dashboard / UI route fallback
```

Production frontend requests use relative `/api/health`, `/api/events`, and `/api/scenarios` URLs. No localhost backend address is embedded in the default production build, and no cross-origin access is needed. Development retains the existing explicit CORS allowlist for `http://localhost:5173`; it is not widened.

The root Dockerfile has two stages, following Docker's [multi-stage build approach](https://docs.docker.com/build/building/multi-stage/):

1. `node:22-bookworm-slim`: copy npm manifests, run `npm ci`, copy frontend source, and run the TypeScript/Vite production build. The Docker stage forces an empty `VITE_API_BASE_URL`; local environment files are excluded from the build context.
2. `python:3.12-slim-bookworm`: install only backend production dependencies from `pyproject.toml`, install the application, and copy only the compiled frontend output from stage 1. Dependencies are cached separately from application source. Node, frontend node_modules, local virtual environments, and tests are not copied into the runtime image.

The runtime uses unprivileged UID/GID `10001`, listens on `0.0.0.0:8000`, and runs Uvicorn without reload. A Python-standard-library healthcheck checks `GET /api/health` every 30 seconds. No curl dependency or credentials are added. Keep one worker while audit storage is process-local and in-memory.

Build and run from the repository root:

```sh
docker build -t agentgate:local .
docker run --rm --name agentgate-local -p 127.0.0.1:8000:8000 agentgate:local
```

Stop any development backend already using port 8000 first. Open **http://localhost:8000**; the dashboard and API are now served by the same FastAPI process. The host port is bound to loopback for the local demo, while the process inside the container binds to all container interfaces.

Check health and run all scenarios:

```sh
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:8000/api/scenarios
curl -fsS -X POST http://localhost:8000/api/scenarios/normal-support/run
curl -fsS -X POST http://localhost:8000/api/scenarios/prompt-injection/run
curl -fsS -X POST http://localhost:8000/api/scenarios/destructive-approval/run
curl -fsS http://localhost:8000/api/events
```

Expected results remain `SUCCESS` (two executed fake tools), `ATTACK_BLOCKED` (BLOCK / 80 / CRITICAL, executed=false), and `APPROVAL_REQUIRED` (REQUIRE_APPROVAL, executed=false).

When finished, stop the container from another terminal; `--rm` removes it:

```sh
docker stop agentgate-local
```

The image structure and port 8000 are intended for Azure Container Apps, but this milestone does not configure or deploy Azure resources. If targeting an amd64 runtime from an ARM machine, use `docker build --platform linux/amd64 -t agentgate:local .`. Audit events remain ephemeral; container restart or scaling does not provide shared persistence.

## Static hosting without Docker

FastAPI mounts the frontend only if a directory containing `index.html` exists. The local default is `frontend/dist` resolved relative to the repository, not the working directory. Set `FRONTEND_DIST_PATH` to an absolute path to override it; Docker sets `/app/frontend/dist`. Missing builds leave the API usable and `/` returns 404.

The static mount is registered after API routes. Unknown `/api` and `/api/*` paths remain JSON 404s, even for POST/PUT/DELETE. Existing files are served through Starlette's safe static-file handling. Only extensionless UI paths fall back to `index.html`; missing assets and private dot paths do not. The HTML entry point uses `Cache-Control: no-cache` to avoid a stale document referencing old assets. No frontend build is required for backend tests: static-serving tests create tiny temporary fixtures.

To verify the production application locally without Docker:

```sh
npm --prefix frontend run build
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Open http://localhost:8001. This serves the actual production frontend and API from one origin, but is **not** a Docker image or container verification.

Milestone 5 verification in this environment: 173 backend tests and 13 frontend tests passed; TypeScript/Vite build passed. The compiled dashboard was served by FastAPI at http://localhost:8001 and all three scenarios were verified through that same-origin UI, including event-log updates. Docker CLI is unavailable, so the actual image build and container startup remain to be verified on a Docker-capable machine. No test containers were created or left running.

No CI/CD, Azure deployment, persistence, production tools, or real LLM integration was added.
