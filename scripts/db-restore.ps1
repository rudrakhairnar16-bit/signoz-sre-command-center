param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

$container = "signoz-metastore-postgres-0"
$dbUser = "signoz"
$dbName = "signoz"

if (-not (Test-Path $BackupFile)) {
    Write-Host "Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

Write-Host "Restoring SigNoz Postgres DB from $BackupFile ..." -ForegroundColor Cyan
Get-Content $BackupFile | docker exec -i $container psql -U $dbUser -d $dbName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore complete!" -ForegroundColor Green
} else {
    Write-Host "Restore failed!" -ForegroundColor Red
    exit 1
}
