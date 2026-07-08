param(
    [string]$OutputDir = ".\backups"
)

$container = "signoz-metastore-postgres-0"
$dbUser = "signoz"
$dbName = "signoz"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $OutputDir "signoz-backup-$timestamp.sql"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created backup directory: $OutputDir" -ForegroundColor Yellow
}

Write-Host "Backing up SigNoz Postgres DB to $backupFile ..." -ForegroundColor Cyan
docker exec $container pg_dump -U $dbUser -d $dbName --clean --if-exists > $backupFile 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Backup complete: $backupFile ($((Get-Item $backupFile).Length/1KB -as [int]) KB)" -ForegroundColor Green
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}
