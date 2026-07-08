# SigNoz SRE Command Center - Demo Script (PowerShell)
# Run: .\demo\demo.ps1
# Or: powershell -ExecutionPolicy Bypass -File .\demo\demo.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SigNoz SRE Command Center - Demo" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Step 1: Verify services
Write-Host "`n[1/5] Checking service health..." -ForegroundColor Yellow
foreach ($svc in @("fastapi-svc","express-svc","goworker-svc")) {
    $status = (docker inspect $svc --format '{{.State.Status}}') 2>$null
    Write-Host "  $svc : $status"
}

# Step 2: Dashboard link
Write-Host "`n[2/5] SLO Dashboard:" -ForegroundColor Yellow
Write-Host "  http://localhost:8080/dashboard/14d7d7dc-5b6b-44bc-ae64-b190cc420087"

# Step 3: Flood service
Write-Host "`n[3/5] Simulating traffic on fastapi-svc..." -ForegroundColor Yellow
Write-Host "  Running: python auto-remediation/simulate-failure.py --service fastapi-svc --mode flood --count 200"
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "auto-remediation/simulate-failure.py --service fastapi-svc --mode flood --count 200"

# Step 4: AI agent
Write-Host "`n[4/5] AI Agent ready at http://localhost:8501" -ForegroundColor Yellow
Write-Host "  Try asking:"
Write-Host '  - "What services are running?"'
Write-Host '  - "Show me error traces"'
Write-Host '  - "Restart fastapi-svc"'

# Step 5: Trigger webhook
Write-Host "`n[5/5] Triggering auto-remediation webhook..." -ForegroundColor Yellow
try {
    $body = @{name="demo-burn-rate-alert"; service="fastapi-svc"; severity="critical"} | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri http://localhost:9000/remediate -Method Post -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 15
    Write-Host "  Webhook response: $($resp.Content)" -ForegroundColor Green
} catch {
    Write-Host "  Webhook error: $_" -ForegroundColor Red
}

# Verify
Start-Sleep -Seconds 3
Write-Host "`nVerifying services after remediation..." -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri http://localhost:8001/process -UseBasicParsing -TimeoutSec 5
    Write-Host "  FastAPI: PASS" -ForegroundColor Green
} catch { Write-Host "  FastAPI: FAIL" -ForegroundColor Red }
try {
    $r = Invoke-WebRequest -Uri http://localhost:3001/execute -UseBasicParsing -TimeoutSec 5
    Write-Host "  Express: PASS" -ForegroundColor Green
} catch { Write-Host "  Express: FAIL" -ForegroundColor Red }
try {
    $r = Invoke-WebRequest -Uri http://localhost:8081/work -UseBasicParsing -TimeoutSec 5
    Write-Host "  GoWorker: PASS" -ForegroundColor Green
} catch { Write-Host "  GoWorker: FAIL" -ForegroundColor Red }

Write-Host "`nDemo complete!" -ForegroundColor Green
Write-Host "Full observability + AI analysis + automated recovery. All on SigNoz." -ForegroundColor Green
