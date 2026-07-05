#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# dev-local.sh — 원격 main 기준으로 로컬에서 FE+BE를 한 번에 띄운다(mock 데모용).
#   대상: macOS / Linux / Windows Git-Bash.  키·과금 불요(VFS=local, 엔타이틀먼트 override).
#   배포(HF Space cpu-basic + Supabase)가 느려서 발표는 로컬로 도는 게 빠르다.
#
# 사용:  bash scripts/dev-local.sh
#   - origin/main에 정확히 맞춘 뒤(로컬 변경 폐기) 백엔드(:8000)·프런트(:3100) 기동.
#   - Ctrl+C로 프런트를 끄면 백엔드도 함께 정리된다.
# 환경변수(선택): BACKEND_PORT(기본 8000) · FRONTEND_PORT(기본 3100) · NO_SYNC=1(main 동기화 건너뜀)
# 사전조건: git · Python 3.11+ · Node 20+ 설치. (영상 렌더까지 보려면 ffmpeg — mock 데모엔 불요)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3100}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "✗ Python 3.11+ 필요 (python3/python 미발견)"; exit 1; }
command -v node >/dev/null || { echo "✗ Node 20+ 필요"; exit 1; }

# 1) 원격 main 동기화 — origin/main에 정확히 맞춘다(로컬 변경 폐기). NO_SYNC=1이면 건너뜀.
if [ "${NO_SYNC:-0}" != "1" ]; then
  echo "▶ origin/main 동기화 중…"
  git fetch origin main
  git checkout main 2>/dev/null || git checkout -B main origin/main
  git reset --hard origin/main
fi
echo "  현재 커밋: $(git rev-parse --short HEAD)"

# 2) 백엔드 — venv 준비 → 의존성 설치 → uvicorn(백그라운드). VFS=local이라 인증·Supabase 불요.
echo "▶ 백엔드 준비(:$BACKEND_PORT)…"
cd "$ROOT/backend"
[ -d .venv ] || "$PY" -m venv .venv
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; else . .venv/Scripts/activate; fi
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements-deploy.txt
VFS_BACKEND=local ENTITLEMENT_OVERRIDE=1 DEMO_LATENCY_MS=0 \
  python -m uvicorn app.server:app --port "$BACKEND_PORT" &
BE_PID=$!
cd "$ROOT"

# 프런트 종료(Ctrl+C) 시 백엔드도 함께 정리.
cleanup() { kill "$BE_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# 백엔드 헬스 대기(최대 ~20초).
echo -n "  백엔드 기동 대기"
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then echo " ✓"; break; fi
  echo -n "."; sleep 0.5
done

# 3) 프런트 — 의존성 설치 → next dev(포그라운드). 백엔드는 localhost:8000 기본값이라 자동 연결.
echo "▶ 프런트 준비(:$FRONTEND_PORT)…"
cd "$ROOT/frontend"
npm install --no-audit --no-fund
echo "▶ 준비 완료 → http://localhost:$FRONTEND_PORT/cockpit (Mock 모드 ON 후 시연)"
NEXT_PUBLIC_API_BASE="http://localhost:$BACKEND_PORT" npm run dev -- -p "$FRONTEND_PORT"
