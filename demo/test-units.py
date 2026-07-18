"""Unit tests for SLO calculations and formatters."""
import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "auto-remediation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-agent"))

pass_count = 0
fail_count = 0

def check(name, ok, detail=""):
    global pass_count, fail_count
    if ok:
        pass_count += 1
        print(f"  [PASS] {name}")
    else:
        fail_count += 1
        print(f"  [FAIL] {name} - {detail}")

# ---------- 1. poller: compute_burn_rate ----------
from poller import compute_burn_rate, SLO_TARGET

# Mock history: 100 calls, 10 errors over 2 hours (5% error rate, 10x budget burn)
import time
now = time.time()
history = {
    "test-svc": [
        {"ts": now - 7200, "errors": 0, "calls": 0},
        {"ts": now - 3600, "errors": 5, "calls": 50},
        {"ts": now,        "errors": 10, "calls": 100},
    ]
}
import poller as p
p.history = history
burn_rate, budget_pct, hours_left = compute_burn_rate("test-svc")

check("compute_burn_rate returns values", burn_rate is not None)
check("burn_rate > 0 for error service", burn_rate > 0)
check("hours_left is finite", hours_left < 9999)

# ---------- 2. predictor: SLO output format ----------
from mcp_tool import predict_slo, SLO_TARGET as SLO

check("SLO_TARGET is 99.5", SLO == 99.5)

# ---------- 3. Formatters ----------
from mcp_tool import _format_services

sample_services = json.dumps({"data": [
    {"serviceName": "svc1", "numCalls": 100, "numErrors": 5, "errorRate": 5.0, "avgDuration": 5e7, "p99": 1e8},
    {"serviceName": "svc2", "numCalls": 50, "numErrors": 1, "errorRate": 2.0, "avgDuration": 3e7, "p99": 5e7},
]})
formatted = _format_services(sample_services)
check("format_services shows svc1", "svc1" in formatted)
check("format_services shows error rate", "5.0%" in formatted)

# ---------- 4. Retry logic ----------
from mcp_tool import _call_mcp

retry_result = _call_mcp("signoz_list_services", retries=0)
check("MCP call returns string", isinstance(retry_result, str))
check("MCP error is user-friendly", not retry_result.startswith("Traceback"))

# ---------- 5. slo.yaml validation ----------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
try:
    import yaml
    with open(os.path.join(os.path.dirname(__file__), "..", "slo.yaml")) as f:
        slo_config = yaml.safe_load(f)
    check("slo.yaml loads", slo_config is not None)
    check("slo.yaml has services", "services" in slo_config)
    check("slo.yaml has slo_target", "slo_target" in slo_config)
except Exception as e:
    check("slo.yaml loads", False, str(e))

# ---------- Summary ----------
print()
total = pass_count + fail_count
print(f"RESULTS: {pass_count}/{total} passed, {fail_count} failed")
if fail_count > 0:
    exit(1)
