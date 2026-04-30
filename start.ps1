$Host.UI.RawUI.WindowTitle = "Agility Sprint Dashboard"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Agility Sprint Dashboard (Streamlit)     " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan


# ── Create venv if missing ────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Creating virtual environment ..." -ForegroundColor Green
    py -m venv .venv
}

# ── Activate venv ─────────────────────────────────────────────────────────────
$activateScript = ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    Write-Host "[ERROR] Could not find venv activation script." -ForegroundColor Red
    exit 1
}

# ── Install / upgrade dependencies ────────────────────────────────────────────
Write-Host "[INFO] Installing dependencies ..." -ForegroundColor Green
py -m pip install --quiet --upgrade pip
py -m pip install --quiet -r requirements.txt

# ── Force UTF-8 I/O so non-ASCII chars never crash the console ────────────────
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8       = "1"

# ── Launch Streamlit app ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[INFO] Starting Streamlit on http://localhost:8501" -ForegroundColor Cyan
Write-Host "[INFO] Press Ctrl+C to stop."                       -ForegroundColor Cyan
Write-Host ""

py -m streamlit run main.py --server.port 8501 --server.address 0.0.0.0
