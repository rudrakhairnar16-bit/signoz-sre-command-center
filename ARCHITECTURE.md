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
│  ┌──────────────────────────────────────────────────┐                     │
│  │              Auto-Remediation                     │                     │
│  │  ┌──────────────────┐    ┌────────────────────┐  │                     │
│  │  │ Webhook Receiver │◀───│ AI Agent (LangGraph)│  │                     │
│  │  │ (Flask :9000)    │    │ (Ollama + Streamlit)│  │                     │
│  │  │                  │    │                     │  │                     │
│  │  │ docker compose   │    │ MCP Tool → SigNoz   │  │                     │
│  │  │ restart <svc>    │    │ for queries          │  │                     │
│  │  └──────────────────┘    └────────────────────┘  │                     │
│  └──────────────────────────────────────────────────┘                     │
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
                                              SLO Command Center Dashboard
                                                        ↓
                                              3 Alert Rules (Warning, Critical, Burn Rate)
```

### 2. AI Agent Flow
```
User → Streamlit UI (:8501) → LangGraph Agent
                                   │
                          ┌────────┴────────┐
                          ▼                  ▼
                    MCP HTTP Query    Remediation Webhook
                    (:8000/mcp)       (:9000/remediate)
                          │                  │
                          ▼                  ▼
                      SigNoz API       docker compose restart
```

### 3. Auto-Remediation Flow (Alert → Recovery)
```
SigNoz Alert (Burn Rate > 2x)
       │
       ▼ POST /remediate
Webhook Receiver (Flask :9000)
       │
       ├─ Identify service from alert payload
       ├─ docker compose restart <service>
       ├─ Log remediation event to SigNoz
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
| Dashboard | SigNoz Query Builder | SLO Command Center (7 panels) |
| Alerts | SigNoz Alert Manager | 3-tier alerting |
| AI Agent | LangGraph + Ollama | Natural language querying |
| MCP | SigNoz MCP Server | Structured tool access to SigNoz |
| Webhook | Python Flask | Auto-remediation handler |
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
