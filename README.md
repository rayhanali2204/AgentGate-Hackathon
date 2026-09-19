# AgentGate

**Zero-Trust Security for Autonomous AI Agents**

Every AI tool call is intercepted, evaluated and audited before execution. Milestone 4 adds a React + TypeScript dashboard to the existing Python engine, REST API, and deterministic agent simulations.

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

The frontend defaults to `http://127.0.0.1:8000`. To use another API address, create `frontend/.env.local` containing:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart Vite after changing environment settings. This setting is public build-time configuration, not a place for secrets. The backend allows the exact browser origin `http://localhost:5173`; use that URL, not `http://127.0.0.1:5173`. Vite uses a strict port so it cannot silently switch to an origin rejected by CORS.

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

`npm run preview` serves the production build at http://localhost:5173 while the backend is running. Stop the Vite development server before starting preview on the same port.

Accessibility includes text/icon decision labels, semantic landmarks, labeled filters, keyboard-accessible event selection, visible focus states, error/loading announcements, and reduced-motion support. Typography uses system fonts with no external font requests.

Milestone 4 only: no Docker, CI/CD, Azure, persistence, production tools, or real LLM integration.
