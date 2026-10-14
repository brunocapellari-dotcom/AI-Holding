# Unified AI Holding developer setup (Windows 11). No Docker, no paid cloud provisioning.
# Run from PowerShell: powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\setup-all-projects.ps1
[CmdletBinding()]
param([switch]$SkipInstall, [switch]$SkipClone)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$owner = 'brunocapellari-dotcom'
$names = @(
    'AI-Holding','Hermes-AI-Platform','Research-AI','Second-Brain',
    'AgroLogMT','WHATSAPP_AI','Geopolitical-Watch',
    'Mercado-Financeiro','Sports-Intelligence','Content-Factory',
    'Game-Studio','Personal-Performance-Health-OS'
)
$workspace = Join-Path $env:USERPROFILE 'AI-Holding-Workspace'
$reposDir = Join-Path $workspace 'repos'
New-Item -ItemType Directory -Force -Path $reposDir | Out-Null

function Has-Command([string]$name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}
function Refresh-Path {
    $env:PATH = ((@(
        [Environment]::GetEnvironmentVariable('Path','Machine'),
        [Environment]::GetEnvironmentVariable('Path','User'),
        (Join-Path $env:APPDATA 'npm'),
        (Join-Path $env:USERPROFILE '.local\bin'),
        (Join-Path $env:ProgramFiles 'Git\cmd'),
        (Join-Path $env:ProgramFiles 'GitHub CLI')
    ) | Where-Object { $_ }) -join ';')
}
function Install-IfMissing([string]$program, [string]$wingetId) {
    if (Has-Command $program) { Write-Host "Existing: $program"; return }
    if (-not (Has-Command 'winget')) { throw 'winget not found. Install Microsoft App Installer first.' }
    Write-Host "Installing $wingetId"
    & winget install --exact --id $wingetId --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { Write-Warning "Install failed: $wingetId" }
    Refresh-Path
}
Refresh-Path
if (-not $SkipInstall) {
    Install-IfMissing 'git' 'Git.Git'
    Install-IfMissing 'gh' 'GitHub.cli'
    Install-IfMissing 'node' 'OpenJS.NodeJS.LTS'
    Install-IfMissing 'py' 'Python.Python.3.12'
    Install-IfMissing 'claude' 'Anthropic.ClaudeCode'
    if (-not (Has-Command 'codex')) {
        if (-not (Has-Command 'npm.cmd')) { Write-Warning 'npm missing. Codex CLI not installed.' }
        else {
            & npm.cmd install --global '@openai/codex'
            if ($LASTEXITCODE -ne 0) { Write-Warning 'Codex CLI installation failed.' }
        }
    }
}
Refresh-Path
if (-not (Has-Command 'git')) { throw 'Git is unavailable. Cannot clone repositories.' }

$pending = @()
if (-not $SkipClone) {
    if (Has-Command 'gh') {
        & gh auth status *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'GitHub authentication is required to clone private projects.'
            & gh auth login --hostname github.com --web --git-protocol https
        }
    }
    foreach ($name in $names) {
        $dest = Join-Path $reposDir $name
        $url = 'https://github.com/{0}/{1}.git' -f $owner,$name
        Write-Host "Repository: $name"
        if (-not (Test-Path $dest)) {
            & git clone --depth 1 $url $dest
            if ($LASTEXITCODE -ne 0) { $pending += $name }
            continue
        }
        if (-not (Test-Path (Join-Path $dest '.git'))) {
            Write-Warning "$dest exists and is not a Git repository. Preserved."
            $pending += $name
            continue
        }
        $origin = & git -C $dest remote get-url origin 2>$null
        if ($LASTEXITCODE -ne 0 -or $origin -notmatch [regex]::Escape($name)) {
            Write-Warning "Unexpected remote; preserving $name"
            $pending += $name
            continue
        }
        $dirty = & git -C $dest status --porcelain
        if ($LASTEXITCODE -ne 0 -or $dirty) {
            Write-Warning "Local changes found; preserving $name without pull"
            continue
        }
        & git -C $dest pull --ff-only
        if ($LASTEXITCODE -ne 0) { $pending += $name }
    }
}
$report = Join-Path $workspace 'STATUS-REPOS.txt'
@('AI Holding workspace',("Directory: $reposDir"),("Repos: " + $names.Count),("Pending: " + ($pending -join ', ')),'') |
    Set-Content -Encoding utf8 $report
foreach ($name in $names) {
    $state = if (Test-Path (Join-Path $reposDir "$name\.git")) { 'READY' } else { 'NOT CLONED' }
    Add-Content -Encoding utf8 $report ("{0}: {1}" -f $name,$state)
}
Write-Host "Report: $report"
Write-Host 'Sign in separately in Codex and Claude Code. Credentials are never placed in this script.'
Write-Host 'Codex Cloud: https://chatgpt.com/codex'
Write-Host 'Claude Code Remote: https://claude.ai/code'
Write-Host 'Local agents stop when laptop is off. Use hosted remote sessions for overnight work.'
Write-Host 'No deploy, purchases, paid cloud services, auto-merge, or GitHub Actions were enabled.'