# JB Marker — Claude 세션 지침 (본선 모드)

JB금융 Fin:AI Challenge **본선(2026-07-04~05) 고도화 작업 중**. 발표 5분 + QA 2분 (상위 5팀은 최종 발표 15분 + 5분).
🔴 **제출 마감 7/5(일) 10:30** — 기능명세서·발표자료·GitHub 링크. 마감 후 수정 불가.
본선 원칙: 예선 MVP의 **순수 최적화 우선**, 기능 추가(CUD)는 기능명세 제출 대상이므로 신중히.

## 지금 읽어야 할 문서
- **본선 공식 규정·일정·제출물 요건: `docs/finals/finals-rules.md`** ← 본선 판단 기준
- 본선 계획: `docs/plans/2026-06-30-finals-optimization-plan.md`
- 변경 보고서(제출용): `docs/finals/optimization-report.md`
- QA 대비: `docs/finals/qa-sheet.md`
- 산출물 증빙: `docs/finals/evidence/`
- 기능 추가 기록(CUD): `docs/finals/feature-changelog.md`

## 워크플로 — 작업 크기별 이원화
- **큰 작업**(새 파이프라인 단계·API 계약 변경·복수 모듈에 걸친 기능): 간소 spec(결정사항 위주) → plan → 전용 워크트리에서 구현 → verify → /ship
- **작은 작업**(단일 모듈 수정·디자인 폴리시·문서·프롬프트 튜닝): 바로 구현 → verify → /ship
- 판단 기준: "계약(API·스키마·게이트 봉투)이 바뀌는가, 실패 시 되돌리기 어려운가" → 하나라도 예이면 큰 작업

## 협업 규약 (albert + rkdrn79 — 기능 단위 수시 병렬)
- 브랜치: `feat/<이름>-<주제>` (예: `feat/albert-video-p2`, `feat/rkdrn-review-rag`)
- 통합: main으로 **작은 PR 수시 머지**. PR 직전 `git pull --rebase origin main` 필수
- 같은 파일을 동시에 만지지 않기 — 착수 전에 상대가 그 영역 작업 중인지 확인
- 워크트리: `git worktree add ../jbm-wt-<주제> -b feat/<이름>-<주제> origin/main`
- Claude 병렬 작업 시 **워크트리당 implementer 1명, 순차 실행** (동시 쓰기로 커밋 클로버링 사고 이력 있음). 완료 후 메인 세션이 `git log`로 커밋 직접 검증

## 출하·sync 규칙
- main 머지 후 **Dojaegyum/jb-marker 미러도 push** — /ship 스킬이 자동화. 수동 머지 시에도 잊지 말 것
- CD: main push → Donaldo5406 Actions가 HF Space(백엔드)·Vercel(프런트) 배포

## 기능 추가(CUD) 규칙
새 사용자 기능·화면·엔드포인트를 추가하면 **반드시 `docs/finals/feature-changelog.md`에 즉시 기록**(기능명세 제출 대비). 순수 최적화는 기록 불필요.

## 데모 크리티컬 — 깨면 안 되는 것
- **Mock 데모 파이프라인**(키·과금 없이 전 구간 결정론 완주) — mock 경로의 계약·산출물 변경 금지
- 규제 크리티컬 경로의 결정론: 필수고지·로고 오버레이, grounding, §50 규칙엔진, 크로스페이드 시간 재매핑(고지 노출 보존) — 결정론 테스트 유지
- 영상 필수고지 노출 ≥3초 검증(프론트 + 서버 422 이중)
- HF Space 운영환경 `ENTITLEMENT_OVERRIDE=1` (실 경로 402 방지)

## 검증 명령
- 백엔드: `cd backend && python -m pytest -q` (루트 `.env` 오염 시 오탐 다수 — 격리 주의)
- 프런트: `cd frontend && npm test` / `npm run typecheck`
- 일괄 점검: **/smoke** (테스트 + 라이브 헬스 + 표 보고)

## 스킬 (이 레포에서 세션을 열어야 로드됨)
- **/ship** — 검증 → push → PR → 머지 → main pull → Dojaegyum 미러 sync
- **/docs-refresh** — 마지막 갱신 이후 diff 스캔 → README·보고서·체인지로그 일괄 갱신
- **/smoke** — pytest + vitest + 라이브 헬스체크 일괄

## 소통
한국어. **과장 배제** — 코드로 검증된 것만 서술하고, 미구현·시뮬레이션 범위는 명시한다(제출 문서 전체의 일관 원칙).
