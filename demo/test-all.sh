#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "  SigNoz SRE Command Center - Full Test"
echo "========================================"

pass=0
fail=0
total=0

check() {
  local name="$1"
  local condition="$2"
  local detail="${3:-}"
  total=$((total + 1))
  if [ "$condition" = "true" ]; then
    pass=$((pass + 1))
    echo "  [PASS] $name"
  else
    fail=$((fail + 1))
    echo "  [FAIL] $name - $detail"
  fi
}

echo ""
echo "========== TEST 1/3: Service Endpoints =========="

fastapi=$(curl -s --max-time 5 http://localhost:8001/process || echo "")
check "FastAPI->Express->GoWorker" "$(echo "$fastapi" | grep -q 'completed' && echo true || echo false)" "$fastapi"

express=$(curl -s --max-time 5 http://localhost:3001/execute || echo "")
check "Express->GoWorker" "$(echo "$express" | grep -q 'completed' && echo true || echo false)" "$express"

goworker=$(curl -s --max-time 5 http://localhost:8081/work || echo "")
check "GoWorker" "$(echo "$goworker" | grep -q 'completed' && echo true || echo false)" "$goworker"

echo ""
echo "========== TEST 2/3: MCP Tools =========="

MCP_URL="http://localhost:8000/mcp"
API_KEY="dbe4dc0e-69a7-4245-81cc-37ad39178e04"
HEADERS=("-H" "Content-Type: application/json" "-H" "x-signoz-api-key: $API_KEY")

mcp_call() {
  curl -s --max-time 10 -X POST "$MCP_URL" \
    -H "Content-Type: application/json" -H "x-signoz-api-key: $API_KEY" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"$1\",\"arguments\":${2:-{}}},\"id\":1}"
}

svc_resp=$(mcp_call "signoz_list_services" '{}')
check "MCP list_services returns data" "$(echo "$svc_resp" | grep -q 'serviceName' && echo true || echo false)" "$svc_resp"

dash_resp=$(mcp_call "signoz_list_dashboards" '{}')
check "MCP SLO Dashboard found" "$(echo "$dash_resp" | grep -q 'SLO Command Center' && echo true || echo false)" "$dash_resp"

trace_resp=$(mcp_call "signoz_search_traces" '{"timeRange":"1h","limit":5}')
check "MCP traces return data" "$(echo "$trace_resp" | grep -q 'rows' && echo true || echo false)" "$trace_resp"

log_resp=$(mcp_call "signoz_search_logs" '{"timeRange":"1h","limit":5}')
check "MCP logs endpoint works" "$(echo "$log_resp" | grep -q 'results' && echo true || echo false)" "$log_resp"

alert_resp=$(mcp_call "signoz_list_alerts" '{}')
check "MCP list_alerts works" "$(echo "$alert_resp" | grep -q 'data' && echo true || echo false)" "$alert_resp"

metric_resp=$(mcp_call "signoz_get_metrics" '{"timeRange":"1h"}')
check "MCP get_metrics works" "$(echo "$metric_resp" | grep -q 'data' && echo true || echo false)" "$metric_resp"

doc_resp=$(mcp_call "signoz_search_docs" '{"searchText":"slo","limit":3}')
check "MCP search_docs works" "$(echo "$doc_resp" | grep -q 'data' && echo true || echo false)" "$doc_resp"

echo ""
echo "========== TEST 3/3: Webhook Remediation =========="

health=$(curl -s --max-time 5 http://localhost:9000/health || echo "")
check "Webhook health endpoint" "$(echo "$health" | grep -q '"ok"' && echo true || echo false)" "$health"

for svc in fastapi-svc express-svc goworker-svc; do
  resp=$(curl -s --max-time 15 -X POST http://localhost:9000/remediate \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"test-$svc\",\"service\":\"$svc\"}" || echo "")
  check "Remediate $svc" "$(echo "$resp" | grep -q 'success' && echo true || echo false)" "$resp"
done

echo ""
echo "========== VERIFY Post-Remediation =========="
sleep 3

fastapi2=$(curl -s --max-time 10 http://localhost:8001/process || echo "")
check "FastAPI still up after remediations" "$(echo "$fastapi2" | grep -q 'completed' && echo true || echo false)" "$fastapi2"

express2=$(curl -s --max-time 10 http://localhost:3001/execute || echo "")
check "Express still up after remediations" "$(echo "$express2" | grep -q 'completed' && echo true || echo false)" "$express2"

goworker2=$(curl -s --max-time 10 http://localhost:8081/work || echo "")
check "GoWorker still up after remediations" "$(echo "$goworker2" | grep -q 'completed' && echo true || echo false)" "$goworker2"

echo ""
echo "========================================"
echo "  RESULTS: $pass/$total passed, $fail failed"
echo "========================================"

if [ "$fail" -gt 0 ]; then
  exit 1
else
  exit 0
fi
