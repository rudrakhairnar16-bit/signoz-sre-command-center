import os
import requests
from typing import Optional

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
SIGNOZ_API_KEY = os.getenv("SIGNOZ_API_KEY", "dbe4dc0e-69a7-4245-81cc-37ad39178e04")
REMEDIATION_URL = os.getenv("REMEDIATION_URL", "http://localhost:9000/remediate")


def _call_mcp(tool_name: str, arguments: dict = None) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }
    resp = requests.post(
        MCP_SERVER_URL,
        json=payload,
        headers={"SIGNOZ-API-KEY": SIGNOZ_API_KEY},
        timeout=30
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        return f"Error: {result['error']}"
    content = result.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts)


def _format_services(raw: str) -> str:
    try:
        import json
        data = json.loads(raw).get("data", [])
        if not data:
            return "No services found."
        lines = [f"Found {len(data)} services:"]
        for s in data:
            lines.append(
                f"  - {s['serviceName']}: {s['numCalls']} calls, "
                f"{s['numErrors']} errors ({s['errorRate']:.1f}%), "
                f"avg {s['avgDuration']/1e6:.0f}ms, p99 {s['p99']/1e6:.0f}ms"
            )
        return "\n".join(lines)
    except Exception:
        return raw


def _format_traces(raw: str) -> str:
    try:
        import json
        data = json.loads(raw)
        results = data.get("data", {}).get("data", {}).get("results", [])
        if not results:
            return "No traces found."
        lines = [f"Found traces:"]
        for r in results:
            rows = r.get("rows") or []
            for row in rows[:10]:
                ts = row.get("timestamp", "")
                dur = row.get("durationNano", 0)
                svc = row.get("serviceName", "")
                op = row.get("operation", "")
                status = row.get("statusCode", "")
                lines.append(f"  [{ts}] {svc}/{op} - {int(dur)/1e6:.0f}ms status={status}")
        return "\n".join(lines) if len(lines) > 1 else "No trace rows found."
    except Exception:
        return raw


def _format_logs(raw: str) -> str:
    try:
        import json
        data = json.loads(raw)
        results = data.get("data", {}).get("data", {}).get("results", [])
        if not results:
            return "No logs found."
        lines = [f"Found logs:"]
        for r in results:
            rows = r.get("rows") or []
            for row in rows[:10]:
                ts = row.get("timestamp", "")
                body = row.get("body", "")
                sev = row.get("severityText", "")
                lines.append(f"  [{ts}] {sev}: {body}")
        return "\n".join(lines) if len(lines) > 1 else "No log rows found."
    except Exception:
        return raw


def _format_alerts(raw: str) -> str:
    try:
        import json
        data = json.loads(raw).get("data", [])
        if not data:
            return "No alert rules configured."
        lines = [f"Alert rules ({len(data)}):"]
        for a in data:
            lines.append(f"  - {a.get('alertName', a.get('alert', 'Unknown'))} [{a.get('severity', '?')}] enabled={a.get('enabled', '?')}")
        return "\n".join(lines)
    except Exception:
        return raw


def _format_dashboards(raw: str) -> str:
    try:
        import json
        data = json.loads(raw).get("data", [])
        if not data:
            return "No dashboards found."
        lines = [f"Dashboards ({len(data)}):"]
        for d in data:
            lines.append(f"  - {d.get('title', d.get('data', {}).get('title', 'Unnamed'))}")
        return "\n".join(lines)
    except Exception:
        return raw


def _format_metrics(raw: str) -> str:
    try:
        import json
        data = json.loads(raw).get("data", [])
        if not data:
            return "No metrics found."
        lines = [f"Metrics:"]
        for m in data:
            lines.append(f"  - {m.get('metricName', '?')}: {m.get('value', '?')}")
        return "\n".join(lines)
    except Exception:
        return raw


def list_services(time_range: str = "1h", limit: int = 50) -> str:
    raw = _call_mcp("signoz_list_services", {"timeRange": time_range, "limit": limit})
    return _format_services(raw)


def search_traces(service_name: str = "", time_range: str = "1h", limit: int = 10) -> str:
    args = {"timeRange": time_range, "limit": limit}
    if service_name:
        args["service"] = service_name
    raw = _call_mcp("signoz_search_traces", args)
    return _format_traces(raw)


def search_logs(service_name: str = "", time_range: str = "1h", severity: str = "", limit: int = 10) -> str:
    args = {"timeRange": time_range, "limit": limit}
    if service_name:
        args["service"] = service_name
    if severity:
        args["severity"] = severity
    raw = _call_mcp("signoz_search_logs", args)
    return _format_logs(raw)


def list_alerts() -> str:
    raw = _call_mcp("signoz_list_alerts", {})
    return _format_alerts(raw)


def list_dashboards() -> str:
    raw = _call_mcp("signoz_list_dashboards", {})
    return _format_dashboards(raw)


def get_metrics(time_range: str = "1h") -> str:
    raw = _call_mcp("signoz_list_metrics", {"timeRange": time_range})
    return _format_metrics(raw)


def search_docs(query_text: str, limit: int = 5) -> str:
    return _call_mcp("signoz_search_docs", {"searchText": query_text, "limit": limit})


def remediate_service(service: str) -> str:
    payload = {
        "name": "agent-triggered-remediation",
        "service": service,
        "severity": "critical",
        "source": "ai-agent",
        "message": f"AI agent triggered remediation for {service}"
    }
    try:
        resp = requests.post(REMEDIATION_URL, json=payload, timeout=15)
        return resp.json().get("status", "unknown")
    except Exception as e:
        return f"failed: {str(e)}"
