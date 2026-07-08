# SigNoz SRE Command Center

> **Team:** Rudra Khairnar & Het Patel — KPGU  
> **Event:** [Agents of SigNoz Hackathon](https://github.com/SigNoz/signoz) — Track 2: Signals & Dashboards  
> **Problem:** SRE teams lack a unified SLO dashboard with AI-driven analysis and automated remediation for microservice incidents.

**Full observability + AI analysis + automated recovery. All on SigNoz.**

## Architecture

```
Services → OpenTelemetry → SigNoz (Query Builder + Dashboards + Alerts)
                                                            ↓
                          ┌─────────────────────────────────┴─────────────────────────────────┐
                          │                                                                   │
                          ▼                                                                   ▼
                   AI Agent (LangGraph + Ollama/Groq)                               Auto-Remediation Webhook
                   (natural language queries)                                      (docker restart on alert)
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full diagram.

## Features

### Phase 1 — SigNoz Deployment
- SigNoz deployed via [Foundry](https://github.com/SigNoz/foundry) with MCP server enabled
- Single-command setup: `foundry deploy`

### Phase 2 — 3x Manual OTel Instrumentation
| Service | Language | Framework | Port |
|---------|----------|-----------|------|
| FastAPI | Python | FastAPI + OpenTelemetry SDK | 8001 |
| Express | Node.js | Express + OpenTelemetry SDK | 3001 |
| Go Worker | Go | net/http + OpenTelemetry SDK | 8081 |

- Distributed traces spanning all 3 services
- Structured logs with trace_id correlation
- Custom span attributes (slo_tier, service.name)
- otel-demo-lite running alongside (15+ supplementary services)

### Phase 3 — SLO Command Center Dashboard + Alerts

**Dashboard (7 panels):**
- SLO Target Gauge (current SLO %)
- Error Budget Remaining (%)
- Active Alert Count
- Services Monitored (18 total)
- p99 Latency Time Series
- Error Rate Time Series
- Trace-Log Correlation Table

**3 Alert Rules:**
| Alert | Condition | Severity | Channel |
|-------|-----------|----------|---------|
| Error Budget Warning | EB < 50% | Warning | Slack |
| Error Budget Critical | EB < 20% | Critical | PagerDuty + Email |
| Burn Rate Critical | Burn rate > 2x for 10 min | Critical | Webhook |

### Phase 4 — AI Agent (MCP + LangGraph + Ollama/Groq)

- **SigNoz MCP Server**: Structured tool access to SigNoz (services, traces, logs, alerts, dashboards, metrics, docs)
- **LangGraph Agent**: `create_react_agent` with reasoning loop
- **Multi-Provider LLM**: Supports Ollama (local, default), Groq (free tier, fast), Gemini, Claude, DeepSeek
- **Configurable via `.env`**: Set `LLM_PROVIDER` and the matching API key
- **Streamlit UI**: Chat interface at http://localhost:8501

**Example queries:**
- "What services are running?"
- "Show me error traces from the last hour"
- "What are my p99 latencies?"
- "Check logs for express-svc"

### Phase 5 — Auto-Remediation

- **Webhook Receiver** (Flask, port 9000): Listens for alert webhooks, restarts failing containers
- **AI-Integrated**: Agent can detect issues via MCP and trigger `signoz_remediate` tool
- **Failure Simulator**: Flood or stop a service to demonstrate the recovery loop
- **Flow**: Alert → Webhook → `docker compose restart` → Verified recovery

### Bonus — CI Pipeline (GitHub Actions)

- **`.github/workflows/ci.yml`** — runs on push/PR to `main`
- Checks Python syntax across all `.py` files
- Installs dependencies and builds Docker images
- Ensures every commit passes basic quality gates

### Bonus — Database Backup & Restore

One-liner scripts to protect your SigNoz configuration:

| Script | Usage |
|--------|-------|
| `scripts/db-backup.ps1` | `.\scripts\db-backup.ps1` (Windows) |
| `scripts/db-restore.ps1` | `.\scripts\db-restore.ps1 backups\signoz-backup-....sql` |
| `scripts/db-backup.sh` | `bash scripts/db-backup.sh` (Linux/macOS) |
| `scripts/db-restore.sh` | `bash scripts/db-restore.sh backups/signoz-backup-....sql` |

Custom container name: pass as `-ContainerName` (PowerShell) or first arg (bash).

### Bonus — Additional Dashboards

Two more dashboard JSONs live in `dashboards/`:

| Dashboard | File | Purpose |
|-----------|------|---------|
| Service Health | `dashboards/service-health.json` | Per-service p99 latency, error rate, request rate |
| Error Budget Tracker | `dashboards/error-budget.json` | Remaining budget, burn rate, SLO compliance over time |

Import via SigNoz UI: **Dashboards → Import JSON**.

## Setup Guide

A complete zero-to-running guide. Estimated time: **30–45 min**.

### Prerequisites

| Tool | Version | Check command | Install link |
|------|---------|---------------|--------------|
| Docker Desktop | 29+ | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Foundry CLI | ≥0.2 | `foundryctl version` | [github.com/SigNoz/foundry](https://github.com/SigNoz/foundry) |
| Ollama (optional) | ≥0.31 | `ollama --version` | [ollama.com](https://ollama.com/download) |
| Python | 3.12+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| Git | any | `git --version` | [git-scm.com](https://git-scm.com/downloads) |

### Step 1 — Clone the Repository

```bash
git clone https://github.com/rudrakhairnar16-bit/signoz-sre-command-center.git
cd signoz-sre-command-center
```

### Step 2 — Deploy SigNoz (via Foundry)

```bash
foundry deploy
```

This starts: SigNoz UI, ClickHouse, PostgreSQL, OTel Collector, MCP Server, Alert Manager.  
Wait until all containers are healthy (`docker ps` shows `healthy` for `signoz-signoz-0`).

**Verify:** Open http://localhost:8080 — you should see the SigNoz login page.  
Login: `admin@signoz.io` / `Admin@12345!`

> **Note:** Foundry pulls images and provisions containers. First run takes 5–10 min.  
> If port 8080 is already in use, edit `pours/deployment/compose.yaml` and change the port mapping.

### Step 3 — Choose Your LLM Provider

The agent supports multiple LLM backends. Pick one:

**Option A — Ollama (local, free, no API key)**
```bash
ollama pull llama3.2:3b
```
Downloads a 2 GB model. Verify: `ollama list` should show `llama3.2:3b`.

**Option B — Groq (free tier, fast, cloud)**
1. Get a free API key at https://console.groq.com/keys
2. Configure in `.env` (see next step)

No Ollama needed for Option B.

### Step 4 — Configure Environment Variables

Copy the template and edit it:

```bash
cp .env.example .env
```

Edit `.env` to match your chosen LLM provider:

```env
# For Ollama (default):
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b

# For Groq (uncomment and fill in):
# LLM_PROVIDER=groq
# LLM_MODEL=llama-3.3-70b-versatile
# GROQ_API_KEY=gsk_...
```

> `.env` is gitignored — your API keys stay local.

### Step 6 — Create the Docker Network

The custom services and SigNoz must be on the same Docker network.

```bash
docker network create signoz-network 2>/dev/null || true
```

### Step 7 — Set Up Python Virtual Environment

```bash
python -m venv ai-agent/venv
```

**Windows:**
```bash
ai-agent\venv\Scripts\pip install -r ai-agent\requirements.txt
```

**macOS / Linux:**
```bash
ai-agent/venv/bin/pip install -r ai-agent/requirements.txt
```

This installs: LangChain, LangGraph, Ollama/Groq clients, Streamlit, Flask, httpx, etc.

### Step 8 — Build & Start Custom Services

Three instrumented microservices that form a request chain:  
`FastAPI (Python) → Express (Node.js) → GoWorker (Go)`

```bash
cd services
docker compose up -d --build
cd ..
```

**Verify all 3 are running:**
```bash
docker ps --filter "name=(fastapi|express|goworker)" --format "table {{.Names}}\t{{.Status}}"
```

**Test the request chain:**
```bash
curl http://localhost:8001/process
```

Expected response:
```json
{"service":"fastapi-svc","express_result":{"service":"express-svc","goworker_result":{"result":"work_done","service":"goworker-svc","status":"completed"}}}
```

### Step 9 — Verify Observability Data in SigNoz

1. Open http://localhost:8080
2. Go to **Services** tab → you should see at least 3 + otel-demo-lite services
3. Go to **Traces** tab → filter by `fastapi-svc` → traces should appear (may take 30s)
4. Go to **Dashboards** → **SLO Command Center** → all 7 panels rendering

> **No services visible?** Hit the endpoint a few times: `for i in 1 2 3 4 5; do curl -s http://localhost:8001/process > /dev/null; done`. Then refresh SigNoz.

### Step 10 — Inject the Dashboard & Alert Rules

The SLO Command Center dashboard and 3 alert rules are stored in PostgreSQL.  
Run the following to insert them (one-time):

```bash
# Windows (PowerShell):
powershell -Command "& { ai-agent\venv\Scripts\python -c "from mcp_tool import query_signoz; print('Dashboard ready')" }"

# Or import via SigNoz UI:
# Dashboards → Import JSON → select dashboards/slo-command-center.json
```

> **Note:** The dashboard was pre-inserted during development. If you don't see it, import manually from `dashboards/slo-command-center.json` via the SigNoz UI.

### Step 11 — Start the AI Agent

The agent auto-loads `.env` — just start it.

```bash
cd ai-agent
```

**Windows:**
```bash
venv\Scripts\streamlit run app.py
```

**macOS / Linux:**
```bash
venv/bin/streamlit run app.py
```

Open http://localhost:8501 in your browser.

> **Note:** If using Ollama, make sure it's running first (`ollama serve &`).  
> If using Groq, just ensure `.env` has your `GROQ_API_KEY` — no separate server needed.

**Test it with:**
- "What services are running?"
- "Show me traces from the last hour"
- "Restart fastapi-svc"

### Step 12 — Start the Auto-Remediation Webhook

Open a **second terminal** and run:

```bash
cd signoz-sre-command-center
```

**Windows:**
```bash
ai-agent\venv\Scripts\python auto-remediation\webhook.py
```

**macOS / Linux:**
```bash
ai-agent/venv/bin/python auto-remediation/webhook.py
```

**Verify:**
```bash
curl http://localhost:9000/health
# → {"status":"ok","timestamp":"..."}
```

### Step 13 — Run the Demo

**Option A — Webhook-only test:**
```bash
python auto-remediation/simulate-failure.py --mode webhook-only --service fastapi-svc
# → Sends a fake alert → webhook restarts the container
```

**Option B — Full flood + recovery demo:**
```bash
python auto-remediation/simulate-failure.py --mode flood --service fastapi-svc --count 500
# → floods the service with 500 requests → triggers webhook → container restarts
```

**Option C — One-click PowerShell demo (Windows):**
```powershell
powershell -ExecutionPolicy Bypass -File demo/demo.ps1
```

**Option D — Bash demo (WSL / Linux / macOS):**
```bash
bash demo/demo.sh
```

## Key URLs

| Service | URL | Purpose |
|---------|-----|---------|
| SigNoz UI | http://localhost:8080 | Dashboards, traces, logs, metrics |
| AI Agent | http://localhost:8501 | Natural-language chat with SigNoz data |
| Remediation Webhook | http://localhost:9000/health | Auto-recovery endpoint |
| FastAPI Service | http://localhost:8001/process | Entry-point microservice |
| Express Service | http://localhost:3001/execute | Middle microservice |
| Go Worker | http://localhost:8081/work | Leaf microservice |

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Problem | Cause | Fix |
|---------|-------|------|
| `network signoz-network not found` | Network not created | `docker network create signoz-network` |
| Services won't start | Port conflict | Change port in `services/docker-compose.yaml` |
| MCP returns 403 | API key missing | Set `SIGNOZ_API_KEY` in `pours/deployment/compose.yaml` |
| Agent says "tool not found" | LLM not configured | Check `.env` — Ollama needs `ollama serve`, Groq needs valid `GROQ_API_KEY` |
| Agent is very slow | Using local Ollama | Switch to Groq (free tier, 10× faster): set `LLM_PROVIDER=groq` + `GROQ_API_KEY` in `.env` |
| `go mod tidy` fails | Go version too old | Update Dockerfile to `golang:latest` |
| No traces in SigNoz | No traffic generated | `curl http://localhost:8001/process` a few times |
| npm install fails | Wrong package versions | Run `npm install` in `services/express/` |

## Repository Structure

```
signoz-sre-command-center/
├── casting.yaml              # Foundry deployment config
├── pours/deployment/         # Foundry compose output
├── .env.example              # Template for environment variables
├── .github/workflows/        # CI pipeline (GitHub Actions)
├── services/                 # 3 custom instrumented services
│   ├── fastapi/              # Python + OTel SDK
│   ├── express/              # Node.js + OTel SDK
│   └── goworker/             # Go + OTel SDK
├── ai-agent/                 # LangGraph AI agent (multi-provider)
│   ├── mcp_tool.py           # MCP JSON-RPC wrapper
│   ├── agent.py              # LangGraph react agent
│   └── app.py                # Streamlit chat UI
├── auto-remediation/         # Webhook receiver + simulator
│   ├── webhook.py            # Flask webhook (port 9000)
│   └── simulate-failure.py   # Traffic flood / service stop
├── scripts/                  # DB backup & restore scripts
│   ├── db-backup.ps1         # PowerShell backup
│   ├── db-restore.ps1        # PowerShell restore
│   ├── db-backup.sh          # Bash backup
│   └── db-restore.sh         # Bash restore
├── dashboards/               # Exported dashboard JSONs
│   ├── slo-command-center.json
│   ├── service-health.json   # Per-service health metrics
│   └── error-budget.json     # Error budget tracker
├── alerts/                   # Alert rule documentation
├── opentelemetry-demo-lite/  # Supplementary demo services
├── ARCHITECTURE.md           # System architecture diagram
└── README.md                 # This file
```

## Tech Stack

| Category | Tools |
|----------|-------|
| Observability | SigNoz, OpenTelemetry, ClickHouse |
| Instrumentation | Python OTel SDK, Node.js OTel SDK, Go OTel SDK |
| AI/ML | LangGraph, Ollama / Groq / Gemini / Claude / DeepSeek, Streamlit |
| Backend | FastAPI, Express.js, Go, Python Flask |
| Infrastructure | Docker, Docker Compose, Foundry |

## Demo Script (2 minutes)

| Time | Scene |
|------|-------|
| 0:00 | Normal ops — Green dashboard, healthy SLOs |
| 0:15 | Incident — Run failure simulator, latency spikes, EB burns |
| 0:35 | AI analysis — "What caused the latency spike?" → Agent diagnoses |
| 0:55 | Auto-remediation — Burn rate alert → Webhook → Service restart |
| 1:15 | Recovery — Dashboard turns green, AI reports impact |
| 1:35 | Closing — Architecture overview |

## Team

- **Rudra Khairnar** — Instrumentation, MCP, AI Agent, Auto-remediation
- **Het Patel** — Dashboard, Alerts, Demo, Documentation
