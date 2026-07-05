# ─────────────────────────────────────────────────────────────────────────────
# dev-local.ps1 — 원격 main 기준으로 로컬에서 FE+BE를 한 번에 띄운다(mock 데모용, Windows).
#   키·과금 불요(VFS=local, 엔타이틀먼트 override). 배포(HF cpu-basic+Supabase)보다 로컬이 빠름.
#
# 사용:  pwsh -File scripts/dev-local.ps1        (또는 PowerShell에서)  .\scripts\dev-local.ps1
#   - origin/main에 정확히 맞춘 뒤(로컬 변경 폐기) 백엔드(:8000)·프런트(:3100) 기동.
#   - 프런트를 Ctrl+C로 끄면 백엔드도 함께 정리된다.
# 파라미터(선택): -BackendPort 8000 -FrontendPort 3100 -NoSync
# 사전조건: git · Python 3.11+ · Node 20+ 설치.
#   (실행정책 막히면:  powershell -ExecutionPolicy Bypass -File scripts\dev-local.ps1 )
# ─────────────────────────────────────────────────────────────────────────────
param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 3100,
  [switch]$NoSync
)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

foreach ($bin in @("git","python","node","npm")) {
  if (-not (Get-Command $bin -ErrorAction SilentlyContinue)) { throw "✗ '$bin' 필요 — 설치 후 재시도 (Python 3.11+ / Node 20+)" }
}

# 1) 원격 main 동기화 — origin/main에 정확히 맞춤(로컬 변경 폐기). -NoSync면 건너뜀.
if (-not $NoSync) {
  Write-Host "▶ origin/main 동기화 중…"
  git fetch origin main
  git checkout main 2>$null; if ($LASTEXITCODE -ne 0) { git checkout -B main origin/main }
  git reset --hard origin/main
}
Write-Host "  현재 커밋: $(git rev-parse --short HEAD)"

# 2) 백엔드 — venv 준비 → 의존성 설치 → uvicorn(백그라운드 프로세스). VFS=local이라 인증·Supabase 불요.
Write-Host "▶ 백엔드 준비(:$BackendPort)…"
Set-Location (Join-Path $root "backend")
if (-not (Test-Path ".venv")) { python -m venv .venv }
$venvPy = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $venvPy -m pip install -q --upgrade pip
& $venvPy -m pip install -q -r requirements-deploy.txt
$env:VFS_BACKEND = "local"; $env:ENTITLEMENT_OVERRIDE = "1"; $env:DEMO_LATENCY_MS = "0"
$be = Start-Process -FilePath $venvPy `
  -ArgumentList @("-m","uvicorn","app.server:app","--port","$BackendPort") `
  -PassThru -NoNewWindow
Set-Location $root

# 백엔드 헬스 대기(최대 ~20초).
Write-Host -NoNewline "  백엔드 기동 대기"
foreach ($i in 1..40) {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://localhost:$BackendPort/health" | Out-Null; Write-Host " ✓"; break } catch { Write-Host -NoNewline "."; Start-Sleep -Milliseconds 500 }
}

# 3) 프런트 — 의존성 설치 → next dev(포그라운드). 백엔드는 localhost:8000 기본값이라 자동 연결.
Write-Host "▶ 프런트 준비(:$FrontendPort)…"
Set-Location (Join-Path $root "frontend")
npm install --no-audit --no-fund
$env:NEXT_PUBLIC_API_BASE = "http://localhost:$BackendPort"
# NEXT_PUBLIC_DEFAULT_MOCK=1: 로컬은 Mock을 기본 ON으로(키 없어 실 API 호출 시 500·무응답 방지).
$env:NEXT_PUBLIC_DEFAULT_MOCK = "1"
Write-Host "▶ 준비 완료 → http://localhost:$FrontendPort/cockpit (Mock 기본 ON — 키 없이 완주)"
try {
  npm run dev -- -p $FrontendPort
} finally {
  if ($be -and -not $be.HasExited) { Stop-Process -Id $be.Id -Force -ErrorAction SilentlyContinue }
}
