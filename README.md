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
                  AI Agent (LangGraph + Ollama)                                    Auto-Remediation Webhook
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

### Phase 4 — AI Agent (MCP + LangGraph + Ollama)

- **SigNoz MCP Server**: Structured tool access to SigNoz (services, traces, logs, alerts, dashboards, metrics, docs)
- **LangGraph Agent**: `create_react_agent` with reasoning loop
- **Local LLM**: Ollama (llama3.2:3b) — no API key required
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

## Quick Start

### Prerequisites
- Docker Desktop 29+
- Foundry CLI (`foundryctl.exe`)
- Ollama (with llama3.2:3b pulled)
- Python 3.12+ virtual environment in `ai-agent/venv/` (run `python -m venv ai-agent/venv && ai-agent/venv/bin/pip install -r ai-agent/requirements.txt`)

### 1. Deploy SigNoz
```bash
foundry deploy
```

### 2. Create Network & Start Custom Services
```bash
docker network create signoz-network 2>/dev/null || true
cd services
docker compose up -d
```

### 3. Start AI Agent
```bash
cd ai-agent
# Windows: venv\Scripts\streamlit run app.py
# POSIX:   venv/bin/streamlit run app.py
# Open http://localhost:8501
```

### 4. Start Remediation Webhook
```bash
# Windows: ai-agent\venv\Scripts\python auto-remediation\webhook.py
# POSIX:   ai-agent/venv/bin/python auto-remediation/webhook.py
```

### 5. Run Demo
```bash
# Flood a service + trigger auto-remediation:
python auto-remediation/simulate-failure.py --mode flood --service fastapi-svc

# Or just test the webhook:
python auto-remediation/simulate-failure.py --mode webhook-only

# PowerShell demo (Windows):
powershell -ExecutionPolicy Bypass -File demo/demo.ps1
```

## Key URLs

| Service | URL |
|---------|-----|
| SigNoz UI | http://localhost:8080 |
| AI Agent | http://localhost:8501 |
| Remediation Webhook | http://localhost:9000/health |
| FastAPI Service | http://localhost:8001/process |
| Express Service | http://localhost:3001/execute |
| Go Worker | http://localhost:8081/work |

## Repository Structure

```
signoz-sre-command-center/
├── casting.yaml              # Foundry deployment config
├── pours/deployment/         # Foundry compose output
├── services/                 # 3 custom instrumented services
│   ├── fastapi/              # Python + OTel SDK
│   ├── express/              # Node.js + OTel SDK
│   └── goworker/             # Go + OTel SDK
├── ai-agent/                 # LangGraph + Ollama AI agent
│   ├── mcp_tool.py           # MCP JSON-RPC wrapper
│   ├── agent.py              # LangGraph react agent
│   └── app.py                # Streamlit chat UI
├── auto-remediation/         # Webhook receiver + simulator
│   ├── webhook.py            # Flask webhook (port 9000)
│   └── simulate-failure.py   # Traffic flood / service stop
├── dashboards/               # Exported dashboard JSONs
│   └── slo-command-center.json
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
| AI/ML | LangGraph, Ollama (llama3.2:3b), Streamlit |
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
