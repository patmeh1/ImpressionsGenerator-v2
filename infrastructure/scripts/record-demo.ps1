<#
.SYNOPSIS
    Records a browser demo of the Impressions Generator v2 as an mp4 file.

.DESCRIPTION
    Uses Playwright to record a walkthrough of the multi-agent pipeline.
    Converts the webm recording to mp4 using ffmpeg.

.PARAMETER BaseUrl
    The URL of the deployed application.

.EXAMPLE
    .\record-demo.ps1 -BaseUrl "https://impgen2-app-dev.azurecontainerapps.io"
#>

param(
    [string]$BaseUrl = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Impressions Generator v2 — Demo Recording           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Base URL: $BaseUrl" -ForegroundColor White
Write-Host ""

# Step 1: Install Playwright if needed
Write-Host "Step 1: Checking Playwright..." -ForegroundColor Cyan
Push-Location "$ProjectRoot\tests\e2e"
if (-not (Test-Path "node_modules")) {
    npm install @playwright/test
    npx playwright install chromium
}
Write-Host "  ✓ Playwright ready" -ForegroundColor Green

# Step 2: Run the demo recording
Write-Host "Step 2: Recording demo..." -ForegroundColor Cyan
$env:DEMO_BASE_URL = $BaseUrl
npx playwright test demo-recording.spec.ts --headed

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Recording may have partial failures (expected if auth required)" -ForegroundColor Yellow
}

# Step 3: Convert to mp4
Write-Host "Step 3: Converting to mp4..." -ForegroundColor Cyan
$webmFiles = Get-ChildItem -Path "test-results" -Filter "*.webm" -Recurse | Sort-Object LastWriteTime -Descending
if ($webmFiles.Count -gt 0) {
    $webmFile = $webmFiles[0].FullName
    $mp4File = "$ProjectRoot\demo.mp4"

    # Try ffmpeg
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpeg) {
        ffmpeg -i "$webmFile" -c:v libx264 -crf 23 -preset medium -y "$mp4File"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Demo recorded: $mp4File" -ForegroundColor Green
        }
    } else {
        Write-Host "  ⚠ ffmpeg not found. WebM file saved at: $webmFile" -ForegroundColor Yellow
        Write-Host "    Convert manually: ffmpeg -i `"$webmFile`" -c:v libx264 demo.mp4" -ForegroundColor Yellow
        Copy-Item $webmFile "$ProjectRoot\demo.webm"
        Write-Host "  ✓ WebM copied to: $ProjectRoot\demo.webm" -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ No recording files found" -ForegroundColor Red
}

Pop-Location

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
