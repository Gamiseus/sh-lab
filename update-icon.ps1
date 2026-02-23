param (
    [Parameter(Mandatory=$true)]
    [string]$ImagePath
)

# Resolve absolute path for image
$AbsImagePath = Resolve-Path $ImagePath
if (-not $AbsImagePath) {
    Write-Error "Image not found at: $ImagePath"
    exit 1
}

$FrontendDir = Join-Path $PSScriptRoot "frontend"

if (-not (Test-Path $FrontendDir)) {
    Write-Error "Frontend directory not found at: $FrontendDir"
    exit 1
}

Write-Host "generating icons from $AbsImagePath..." -ForegroundColor Cyan
Push-Location $FrontendDir

# Run tauri icon command
# Note: npm run passes arguments after --
npm run tauri icon "$AbsImagePath"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully updated app icons!" -ForegroundColor Green
    Write-Host "Note: You may need to rebuild or restart the app to see changes." -ForegroundColor Yellow
} else {
    Write-Error "Failed to update icons."
}

Pop-Location
