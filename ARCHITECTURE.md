# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SigNoz SRE Command Center                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                                │
│  │ FastAPI  │──▶│ Express  │──▶│ GoWorker │  ← 3 instrumented services     │
│  │ (Python) │   │ (Node.js)│   │ (Go)     │    (manual OTel)               │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘                                │
│       │              │              │                                       │
│       └──────┬───────┘──────┬───────┘                                       │
│              │              │                                               │
│              ▼              ▼                                               │
│  ┌─────────────────────┐                                                   │
│  │  OTel Collector     │  ← Batch, enrich, export                         │
│  │  (svc-otel-collector)│                                                  │
│  └──────────┬──────────┘                                                   │
│             │                                                              │
│             ▼                                                              │
│  ┌──────────────────────────────────────────────┐                         │
│  │              SigNoz Platform                  │                         │
│  │  ┌────────┐  ┌──────────┐  ┌──────────────┐  │                         │
│  │  │Query   │  │Dashboard │  │Alert Manager │  │                         │
│  │  │Builder │  │(SLO Cmd  │  │(3 rules)     │  │                         │
│  │  │        │  │ Center)  │  │              │  │                         │
│  │  └────────┘  └──────────┘  └──────┬───────┘  │                         │
│  │  ┌────────┐  ┌──────────┐        │          │                         │
│  │  │Traces  │  │Logs      │        │          │                         │
│  │  │(Click- │  │(Click-   │        │          │                         │
│  │  │ house) │  │ house)   │        │          │                         │
│  │  └────────┘  └──────────┘        │          │                         │
│  └──────────────────────────────────┼───────────┘                         │
│                                     │                                      │
│                                     ▼                                      │
│  ┌──────────────────────────────────────────────────────┐                 │
│  │              Auto-Remediation                         │                 │
│  │  ┌──────────────────┐  ┌──────────────────────┐      │                 │
│  │  │ Webhook Receiver │◀─│ AI Agent (LangGraph)  │      │                 │
│  │  │ (Flask :9000)    │  │ (Ollama/Groq +        │      │                 │
│  │  │                  │  │  Streamlit)            │      │                 │
│  │  │ docker compose   │  │                       │      │                 │
│  │  │ restart <svc>    │  │ MCP Tool → SigNoz     │      │                 │
│  │  └────────┬─────────┘  └───────────────────────┘      │                 │
│  │           ▲                                            │                 │
│  │  ┌────────┴──────────┐                                │                 │
│  │  │  Poller (sigNoz   │  ← polls error rates           │                 │
│  │  │  API → webhook)   │    every 30s                   │                 │
│  │  └───────────────────┘                                │                 │
│  └──────────────────────────────────────────────────────┘                 │
│                                                                             │
│  ┌──────────────────────────────────────────────┐                         │
│  │              otel-demo-lite                   │                         │
│  │  (frontend, cart, checkout, payment, email,   │                         │
│  │   shipping, recommendation, ad, etc.)         │                         │
│  └──────────────────────────────────────────────┘                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Observability Pipeline
```
Services → OTLP Exporter → OTel Collector → SigNoz (ClickHouse + Query Builder)
                                                        ↓
                                              Dashboards (3 JSON exports):
                                                - SLO Command Center
                                                - Service Health (p99, error rate)
                                                - Error Budget Tracker
                                                        ↓
                                              3 Alert Rules (Warning, Critical, Burn Rate)
                                                └── (pre-existing bug — alerts never fire)
```

### 2. AI Agent Flow (multi-provider LLM)
```
User → Streamlit UI (:8501) → LangGraph Agent
                                   │
                          ┌───────┴────────┐
                          ▼                 ▼
                    MCP HTTP Query    Remediation Webhook
                    (:8000/mcp)       (:9000/remediate)
                          │                 │
                          ▼                 ▼
                      SigNoz API      docker compose restart

LLM backends (configurable via .env):
  - Ollama (local, default: llama3.2:3b)
  - Groq (cloud, fast: llama-3.3-70b-versatile)
  - Gemini / Claude / DeepSeek (optional)
```

### 3. Poller Flow (Alertmanager bypass)
```
Poller (Py :9001) ← every 30s ← SigNoz API (service error rates)

       │  error rate > threshold (e.g. 10%)
       ▼ POST /remediate
Webhook Receiver (Flask :9000)
       │
       ├─ docker compose restart <service>
       ├─ Log remediation event to SigNoz
       └─ Return status
```

### 4. Auto-Remediation Flow (AI Agent triggered)
```
User → AI Agent "Restart express-svc"
                    │
                    ▼ signoz_remediate tool
              Webhook Receiver (Flask :9000)
                    │
                    ├─ docker compose restart <service>
                    └─ Return status
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| SigNoz | Foundry-deployed | Observability backend |
| FastAPI Service | Python + OpenTelemetry | Custom instrumented service |
| Express Service | Node.js + OpenTelemetry | Custom instrumented service |
| Go Worker | Go + OpenTelemetry | Custom instrumented service |
| OTel Collector | OpenTelemetry Collector | Batch, enrich, route telemetry |
| Dashboards (3) | SigNoz Query Builder | SLO, Service Health, Error Budget |
| Alerts | SigNoz Alert Manager | 3-tier alerting (pre-existing bug) |
| Poller | Python + requests | Polls SigNoz API, triggers webhook |
| AI Agent | LangGraph + Ollama/Groq | Natural language querying |
| MCP | SigNoz MCP Server | 8 typed tools to query SigNoz |
| Webhook | Python Flask | Auto-remediation handler |
| CI | GitHub Actions | Lint + build on push/PR |
| Backup | pg_dump scripts | PowerShell + Bash for DB backup/restore |
| Demo Stack | opentelemetry-demo-lite | Supplementary telemetry |

## Port Mapping

| Port | Service |
|------|---------|
| 8080 | SigNoz UI |
| 8000 | SigNoz MCP Server |
| 8501 | Streamlit AI Agent |
| 9000 | Auto-Remediation Webhook |
| 8001 | FastAPI Service |
| 3001 | Express Service |
| 8081 | Go Worker Service |
