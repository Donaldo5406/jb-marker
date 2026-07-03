---
name: smoke
description: Use when 데모 전·머지 전·아침 시작 시 시스템 상태를 한 번에 점검할 때 — 백엔드 pytest·프런트 vitest·라이브 헬스(Vercel/HF Space)를 실행하고 한 장 표로 보고. "스모크", "상태 점검", "데모 전 체크", "다 살아있어?" 트리거.
---

# /smoke — 상태 일괄 점검

목적: "무대에서야 문제를 발견"하는 사고 방지. 각 점검은 독립 — **하나 실패해도 나머지를 전부 실행**하고 표로 모아 보고한다.

## 점검 항목

### 1. 백엔드 테스트
```bash
cd backend && python -m pytest -q
```
- ⚠️ 루트 `.env` 오염 시 다수 오탐(과거 27 fail 사례). 실패가 비정상적으로 많으면 env 격리 후 재실행.

### 2. 프런트 테스트 + 타입
```bash
cd frontend && npm test
cd frontend && npm run typecheck
```

### 3. 라이브 헬스
```bash
curl -s -o /dev/null -w "%{http_code}" https://jb-marker.vercel.app          # 기대: 200
curl -s https://doss-8b-instruct-jb-marker.hf.space/health                   # 기대: ok
```

### 4. 배포 파이프라인
```bash
gh run list -L 3   # Donaldo Actions 최근 실행 상태 (접근 가능 시)
```

### 5. (라이브 데모 전날만) 백엔드 부팅 점검 로그
HF Space 로그에서 **ffmpeg·한글(CJK) 폰트 탐지 로그** 확인 — 렌더 가능 여부를 무대 전에 안다.

## 보고 형식
```
| 항목 | 결과 | 비고 |
| 백엔드 pytest | ✅ 338 passed | |
| 프런트 vitest | ✅ 187 passed | |
| typecheck | ✅ | |
| Vercel 웹앱 | ✅ 200 | |
| HF /health | ✅ ok | |
| CD 최근 런 | ✅ | |
```
실패 항목은 원인 1줄 + 조치 제안 1줄. 전부 통과면 "데모 가능 상태"로 종결.
