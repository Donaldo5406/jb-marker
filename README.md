# JB Marker

금융 마케팅 홍보물 기획·디자인·검토·발송을 하나의 파이프라인으로 잇는 멀티 기능 에디터 플랫폼.
mvp/03-marketing의 리팩토링 후속 — 새 독립 레포로 재출발한다.

## 구조

- `frontend/` — Next.js(App Router) + TypeScript + Tailwind + motion → Vercel
- `backend/` — FastAPI + Python → HF Space
- `docs/` — 자체완결 SSOT
  - `Refactor.md` — 기획 SSOT (배경·핵심 아키텍처·운영 결정 C1~C4·DoD·Non-goals)
  - `design/` — 백엔드/프론트 설계 문서 10종
  - `specs/` — 마일스톤별 설계(spec), `plans/` — 구현계획(plan) (brainstorming → writing-plans 산출물)

## 파이프라인

랜딩 → 콕핏(Workspace/History/Setting) → BrainStorming → Design → Review → Deploy

## 원칙

- **SSOT = 이 레포의 코드 + `docs/`.** 외부(01·02 주제 코드/문서)는 비참조.
- 상태의 유일한 주인 = 저장소(로컬 우선 → Supabase). LangGraph 미사용.
- AI 산출은 항상 VFS를 경유해 서빙(grounding·메타·History 자동 부착).

## 빌드 마일스톤

| # | 마일스톤 | 상태 |
|---|---|---|
| M0 | 레포 스캐폴드 & 디자인 시스템 | 완료 |
| M1 | VfsStore + Marker API 게이트웨이 | 완료 |
| M2 | 프론트 셸: 랜딩 + 콕핏 + 네비게이션 (E2E) | 완료 (PR #1) |
| M3 | BrainStormingStudio | 대기 (다음) |
| M4 | DesignStudio | 대기 |
| M5 | ReviewStudio | 대기 |
| M6 | DeployStudio | 대기 |
| M7 | History + 통합·배포 | 대기 |

## 로컬 실행

백엔드:

```
cd backend && pip install -e ".[dev]" && uvicorn app.server:app --reload
```

프론트:

```
cd frontend && npm install && npm run dev
```

테스트: `cd backend && pytest` · `cd frontend && npm run test && npm run build`

환경변수는 각 디렉터리의 `.env.example`를 복사해 사용한다(로컬-우선 — 키 없어도 부팅).
