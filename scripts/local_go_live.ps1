$ErrorActionPreference = "Stop"

docker compose version | Out-Null
docker compose up --build -d

$ready = $false
for ($attempt = 1; $attempt -le 36; $attempt++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/ready" -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 5
    }
}

if (-not $ready) {
    Write-Error "Holding did not become ready. Check: docker compose logs --tail=120 api pmo-worker knowledge-worker"
}

Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/health" -TimeoutSec 3 | Select-Object -ExpandProperty Content
Write-Host "Holding owner console: http://127.0.0.1:8080/"
docker compose ps
