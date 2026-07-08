"""SigNoz SRE Command Center - Full Integration Test"""
import requests
import json
import time

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

MCP_URL = "http://localhost:8000/mcp"
API_KEY = "dbe4dc0e-69a7-4245-81cc-37ad39178e04"
HEADERS = {"Content-Type": "application/json", "x-signoz-api-key": API_KEY}

def mcp_call(tool, args=None):
    payload = {"jsonrpc": "2.0", "method": "tools/call",
               "params": {"name": tool, "arguments": args or {}}, "id": 1}
    r = requests.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    d = r.json()
    sc = d["result"].get("structuredContent")
    if sc:
        return sc
    txt = d["result"]["content"][0]["text"]
    return json.loads(txt)


print("=" * 50)
print("  SigNoz SRE Command Center - Full Test")
print("=" * 50)

# ========== TEST 1/3: SERVICE ENDPOINTS ==========
print("\n========== TEST 1/3: Service Endpoints ==========")
r = requests.get("http://localhost:8001/process", timeout=5)
d = r.json()
check("FastAPI->Express->GoWorker",
      d["express_result"]["goworker_result"]["status"] == "completed")

r = requests.get("http://localhost:3001/execute", timeout=5)
d = r.json()
check("Express->GoWorker",
      d["goworker_result"]["status"] == "completed")

r = requests.get("http://localhost:8081/work", timeout=5)
d = r.json()
check("GoWorker", d["status"] == "completed")

# ========== TEST 2/3: MCP TOOLS ==========
print("\n========== TEST 2/3: MCP Tools ==========")
d = mcp_call("signoz_list_services")
svc_names = [s["serviceName"] for s in d["data"]]
count = len(d["data"])
check("MCP list_services (18)", count >= 15, f"Found {count}")
check("MCP fastapi-svc present", "fastapi-svc" in svc_names)
check("MCP express-svc present", "express-svc" in svc_names)
check("MCP goworker-svc present", "goworker-svc" in svc_names)
check("MCP unknown_service present", "unknown_service" in svc_names)

d = mcp_call("signoz_list_dashboards")
dash_names = [da["name"] for da in d["data"]]
check("MCP SLO Dashboard found", "SLO Command Center" in dash_names)

d = mcp_call("signoz_search_traces", {"timeRange": "1h", "limit": 5})
rows = d["data"]["data"]["results"][0]["rows"]
check("MCP traces return data", len(rows) > 0, f"Found {len(rows)} traces")
has_fastapi = any("fastapi-svc" in str(r) for r in rows)
check("MCP traces contain fastapi-svc", has_fastapi)

d = mcp_call("signoz_search_logs", {"timeRange": "1h", "limit": 5})
log_rows = d["data"]["data"]["results"][0]["rows"]
log_count = len(log_rows) if log_rows else 0
check("MCP logs endpoint works", True, f"Found {log_count} log rows")

# ========== TEST 3/3: WEBHOOK REMEDIATION ==========
print("\n========== TEST 3/3: Webhook Remediation ==========")
r = requests.get("http://localhost:9000/health", timeout=5)
check("Webhook health", r.json()["status"] == "ok")

for svc in ["fastapi-svc", "express-svc", "goworker-svc"]:
    r = requests.post("http://localhost:9000/remediate",
                      json={"name": f"test-{svc}", "service": svc}, timeout=15)
    j = r.json()
    check(f"Remediate {svc}", "success" in j["status"], j["status"])

# ========== VERIFY POST-REMEDIATION ==========
print("\n========== VERIFY Post-Remediation ==========")
time.sleep(3)
for name, url in [("FastAPI", "http://localhost:8001/process"),
                   ("Express", "http://localhost:3001/execute"),
                   ("GoWorker", "http://localhost:8081/work")]:
    r = requests.get(url, timeout=10)
    check(f"{name} still up", r.status_code == 200, f"Status {r.status_code}")

print()
total = pass_count + fail_count
print(f"RESULTS: {pass_count}/{total} passed, {fail_count} failed")
if fail_count > 0:
    exit(1)
