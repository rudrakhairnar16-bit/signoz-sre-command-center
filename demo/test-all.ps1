Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SigNoz SRE Command Center - Full Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$pass = 0; $fail = 0; $total = 0

# Helper
function Check {
    param($Name, $Condition, $Detail)
    $global:total++
    if ($Condition) { $global:pass++; Write-Host "  [PASS] $Name" -ForegroundColor Green }
    else { $global:fail++; Write-Host "  [FAIL] $Name - $Detail" -ForegroundColor Red }
}

# ========== TEST 1/3: SERVICES ==========
Write-Host "`n========== TEST 1/3: Service Endpoints ==========" -ForegroundColor Yellow
try {
    $fastapi = (Invoke-WebRequest -Uri http://localhost:8001/process -UseBasicParsing -TimeoutSec 5).Content | ConvertFrom-Json
    Check "FastAPI->Express->GoWorker" ($fastapi.express_result.goworker_result.status -eq "completed") $fastapi.express_result.goworker_result.status
} catch { Check "FastAPI->Express->GoWorker" $false $_.Exception.Message }

try {
    $express = (Invoke-WebRequest -Uri http://localhost:3001/execute -UseBasicParsing -TimeoutSec 5).Content | ConvertFrom-Json
    Check "Express->GoWorker" ($express.goworker_result.status -eq "completed") $express.goworker_result.status
} catch { Check "Express->GoWorker" $false $_.Exception.Message }

try {
    $goworker = (Invoke-WebRequest -Uri http://localhost:8081/work -UseBasicParsing -TimeoutSec 5).Content | ConvertFrom-Json
    Check "GoWorker" ($goworker.status -eq "completed") $goworker.status
} catch { Check "GoWorker" $false $_.Exception.Message }

# ========== TEST 2/3: MCP ==========
Write-Host "`n========== TEST 2/3: MCP Tools ==========" -ForegroundColor Yellow
$headers = @{"Content-Type"="application/json"; "x-signoz-api-key"="dbe4dc0e-69a7-4245-81cc-37ad39178e04"}
try {
    $mcp_services = (Invoke-WebRequest -Uri http://localhost:8000/mcp -Method Post -Body '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"signoz_list_services","arguments":{}},"id":1}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json -Depth 10
    $json_svc = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String([System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($mcp_services))))
    $svc_obj = $json_svc | ConvertFrom-Json
    $svc_names = $svc_obj.result.structuredContent.data.serviceName
    Check "MCP list_services (18 services)" ($svc_names.Count -eq 18) "Found $($svc_names.Count)"
    Check "MCP fastapi-svc present" ($svc_names -contains "fastapi-svc") ($svc_names -join ", ")
} catch { Check "MCP list_services" $false $_.Exception.Message }

try {
    $mcp_dash = (Invoke-WebRequest -Uri http://localhost:8000/mcp -Method Post -Body '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"signoz_list_dashboards","arguments":{}},"id":1}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 10).Content
    $dash_names = ($mcp_dash | ConvertFrom-Json).result.structuredContent.data.name
    Check "MCP SLO Dashboard found" ($dash_names -contains "SLO Command Center") ($dash_names -join ", ")
} catch { Check "MCP SLO Dashboard found" $false $_.Exception.Message }

try {
    $mcp_traces = (Invoke-WebRequest -Uri http://localhost:8000/mcp -Method Post -Body '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"signoz_search_traces","arguments":{"timeRange":"1h","limit":5}},"id":1}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 10).Content
    $trace_rows = ($mcp_traces | ConvertFrom-Json).result.structuredContent.data.data.results[0].rows
    Check "MCP search_traces returns data" ($trace_rows.Count -gt 0) "Found $($trace_rows.Count) traces"
} catch { Check "MCP search_traces returns data" $false $_.Exception.Message }

# ========== TEST 3/3: WEBHOOK ==========
Write-Host "`n========== TEST 3/3: Webhook Remediation ==========" -ForegroundColor Yellow
try {
    $health = (Invoke-WebRequest -Uri http://localhost:9000/health -UseBasicParsing -TimeoutSec 5).Content | ConvertFrom-Json
    Check "Webhook health endpoint" ($health.status -eq "ok") $health.status
} catch { Check "Webhook health endpoint" $false $_.Exception.Message }

foreach ($svc in @("fastapi-svc","express-svc","goworker-svc")) {
    try {
        $payload = @{name="test-$svc"; service=$svc} | ConvertTo-Json
        $remediation = (Invoke-WebRequest -Uri http://localhost:9000/remediate -Method Post -Body $payload -ContentType "application/json" -UseBasicParsing -TimeoutSec 15).Content | ConvertFrom-Json
        Check "Remediate $svc" ($remediation.status -match "success") $remediation.status
    } catch { Check "Remediate $svc" $false $_.Exception.Message }
}

# Verify post-remediation
Write-Host "`n========== VERIFY Post-Remediation ==========" -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $fastapi2 = (Invoke-WebRequest -Uri http://localhost:8001/process -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
    Check "FastAPI still up after remediations" ($fastapi2.express_result.goworker_result.status -eq "completed") $fastapi2.express_result.goworker_result.status
} catch { Check "FastAPI still up after remediations" $false $_.Exception.Message }

try {
    $express2 = (Invoke-WebRequest -Uri http://localhost:3001/execute -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
    Check "Express still up after remediations" ($express2.goworker_result.status -eq "completed") $express2.goworker_result.status
} catch { Check "Express still up after remediations" $false $_.Exception.Message }

try {
    $goworker2 = (Invoke-WebRequest -Uri http://localhost:8081/work -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
    Check "GoWorker still up after remediations" ($goworker2.status -eq "completed") $goworker2.status
} catch { Check "GoWorker still up after remediations" $false $_.Exception.Message }

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RESULTS: $pass/$total passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) {"Green"} else {"Red"})
Write-Host "========================================" -ForegroundColor Cyan

if ($fail -gt 0) { exit 1 } else { exit 0 }
