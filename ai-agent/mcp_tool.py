import requests
import json
from typing import Optional

MCP_SERVER_URL = "http://localhost:8000/mcp"
SIGNOZ_API_KEY = "dbe4dc0e-69a7-4245-81cc-37ad39178e04"

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
    result = resp.json()
    if "error" in result:
        return f"Error: {result['error']}"
    content = result.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts)


def query_signoz(query: str) -> str:
    if "service" in query.lower():
        services = _call_mcp("signoz_list_services", {"timeRange": "6h", "limit": 50})
        return f"Services from SigNoz:\n{services}"
    elif "trace" in query.lower():
        service = extract_service_name(query)
        args = {"timeRange": "1h", "limit": 10}
        if service:
            args["service"] = service
        return _call_mcp("signoz_search_traces", args)
    elif "log" in query.lower():
        service = extract_service_name(query)
        args = {"timeRange": "1h", "limit": 10}
        if service:
            args["service"] = service
        if "error" in query.lower():
            args["severity"] = "ERROR"
        return _call_mcp("signoz_search_logs", args)
    elif "alert" in query.lower():
        return _call_mcp("signoz_list_alerts", {})
    elif "dashboard" in query.lower():
        return _call_mcp("signoz_list_dashboards", {})
    elif "metric" in query.lower() or "latency" in query.lower() or "p99" in query.lower():
        return _call_mcp("signoz_list_metrics", {"timeRange": "1h"})
    elif "docs" in query.lower() or "how" in query.lower():
        return _call_mcp("signoz_search_docs", {"searchText": query, "limit": 5})
    else:
        return _call_mcp("signoz_search_docs", {"searchText": query, "limit": 3})


def extract_service_name(query: str) -> Optional[str]:
    services = ["fastapi-svc", "express-svc", "goworker-svc"]
    for s in services:
        if s in query.lower():
            return s
    return None
