#!/bin/bash
# SigNoz SRE Command Center - Demo Script
# Run this to demonstrate the complete flow: monitoring -> alert -> AI analysis -> auto-remediation
#
# Usage:
#   bash demo/demo.sh              # Normal mode (uses & for parallelism)
#   bash demo/demo.sh sequential   # Sequential mode (clearer output)

set -e

MODE="${1:-parallel}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  SigNoz SRE Command Center - Demo${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Step 1: Verify services are healthy
echo -e "${YELLOW}[1/5] Checking service health...${NC}"
for svc in fastapi-svc express-svc goworker-svc; do
    status=$(docker inspect "$svc" --format '{{.State.Status}}')
    echo "  $svc: $status"
done
echo ""

# Step 2: Show SLO dashboard
echo -e "${YELLOW}[2/5] SLO Dashboard is at:${NC}"
echo "  http://localhost:8080/dashboard/14d7d7dc-5b6b-44bc-ae64-b190cc420087"
echo ""

# Step 3: Flood a service to trigger alert conditions
echo -e "${YELLOW}[3/5] Simulating traffic spike on fastapi-svc...${NC}"
if [ "$MODE" = "sequential" ]; then
    python auto-remediation/simulate-failure.py --service fastapi-svc --mode flood --count 200
else
    python auto-remediation/simulate-failure.py --service fastapi-svc --mode flood --count 200 &
    FLOOD_PID=$!
fi
echo ""

# Step 4: AI agent analysis (via MCP)
echo -e "${YELLOW}[4/5] AI agent analyzing system health...${NC}"
echo "  Open http://localhost:8501 and ask:"
echo "  - \"What services are running?\""
echo "  - \"Show me error traces from the last hour\""
echo "  - \"What are my p99 latencies?\""
echo ""

# Step 5: Trigger auto-remediation
echo -e "${YELLOW}[5/5] Triggering auto-remediation...${NC}"
echo "  Sending alert to webhook: http://localhost:9000/remediate"
curl -s -X POST http://localhost:9000/remediate \
    -H "Content-Type: application/json" \
    -d '{"name":"demo-burn-rate-alert","service":"fastapi-svc","severity":"critical","labels":{"service":"fastapi-svc"}}' | python -m json.tool
echo ""

# Wait for flood to finish if in parallel mode
if [ "$MODE" = "parallel" ] && [ -n "$FLOOD_PID" ]; then
    wait $FLOOD_PID 2>/dev/null || true
fi

echo -e "${GREEN}Demo complete!${NC}"
echo -e "${GREEN}Full observability + AI analysis + automated recovery. All on SigNoz.${NC}"
