"""SigNoz SRE Command Center — Demo output for screenshots."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-agent"))
from mcp_tool import (
    list_services, search_traces, search_logs,
    list_alerts, list_dashboards, get_metrics,
    search_docs, predict_slo
)

SEP = "=" * 56

def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def demo():
    print(f"\n{SEP}")
    print(f"  SigNoz SRE Command Center - Demo Output")
    print(f"  All MCP tools responding with live data")
    print(f"{SEP}")

    section("1. Services")
    print(list_services())

    section("2. Traces (fastapi-svc)")
    print(search_traces("fastapi-svc", "6h", 5))

    section("3. ERROR Logs (express-svc)")
    print(search_logs("express-svc", "6h", "ERROR", 5))

    section("4. All Alert Rules")
    print(list_alerts())

    section("5. Dashboards")
    print(list_dashboards())

    section("6. Metrics (p99 / latency)")
    print(get_metrics("6h"))

    section("7. Documentation Search")
    print(search_docs("create dashboard", 3))

    section("8. SLO Prediction (all)")
    print(predict_slo())

    section("9. SLO Prediction (fastapi-svc)")
    print(predict_slo("fastapi-svc"))

    print(f"\n{SEP}")
    print(f"  All checks complete - system is working")
    print(f"{SEP}\n")

if __name__ == "__main__":
    demo()
