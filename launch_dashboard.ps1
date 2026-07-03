# launch_dashboard.ps1
# Commodity Systematic Research Platform — Windows dashboard launcher.
#
# Calls .venv\Scripts\streamlit.exe directly rather than relying on PATH
# resolution, which may find a different Python installation.
# Sets PYTHONPATH so dashboard/components/ imports resolve correctly.
#
# Usage: .\launch_dashboard.ps1

$ScriptDir = $PSScriptRoot
$env:PYTHONPATH = $ScriptDir

$Streamlit = Join-Path $ScriptDir ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $Streamlit)) {
    Write-Error "streamlit.exe not found at $Streamlit"
    Write-Error "Set up the virtual environment first:"
    Write-Error "  python -m venv .venv"
    Write-Error "  .venv\Scripts\activate"
    Write-Error "  pip install -e '.[dev]'"
    exit 1
}

Write-Host "Commodity Systematic Research Platform" -ForegroundColor Cyan
Write-Host "Python:    $ScriptDir\.venv\Scripts\python.exe" -ForegroundColor DarkGray
Write-Host "Dashboard: http://localhost:8501" -ForegroundColor Green
Write-Host ""

& $Streamlit run (Join-Path $ScriptDir "dashboard\app.py")
