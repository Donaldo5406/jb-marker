# Marker BrainStorming 하네스 설계 (Brainstorm Sub-harness)

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" — Marker 모델(브레인스토밍) 하네스(67줄).
> 짝 문서: @design_subharness.md(DesignStudio). 공유 요소: 파일시스템 CRUD 스킬.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 (01·02 비참조)

---

## 0. 전제

- **영감**: 클로드 코드 + superpowers 공식 플러그인. `brainstorming → writing-plans` 2단계 프로세스를 금융 마케팅 도메인으로 채택.
- **입력**: 사용자 멀티턴 대화 + 가상 폴더 리서치 asset(자동 수집 + 사용자 수동 추가).
- **출력**: `spec.md`(Stage A) + `plan.md`(Stage B). `plan.md` = DesignStudio 입력 계약(⓪).
- **"Marker"(브레인스토밍)** = 이 하네스가 씌워진 Claude. 모델 선택 UI 최상단 노출(Refactor 39줄). 디자인 Marker와 동일 6요소 패턴, 도메인만 "기획".
- Refactor.md 41~43줄(1단계 스펙 → 2단계 구현계획)과 정확히 정합.

## ⓪ 정합 계약 (요소 3 — 가장 중요)

`plan.md`는 DesignStudio S0가 파싱하는 모든 요소를 빠짐없이 담아야 한다(@design_subharness.md ⓪·② 기준).

| DesignStudio 요구 | plan.md 보증 항목 |
|---|---|
| S0 디자인 토큰 | palette · font · grid · aspect (creative_direction 시드) |
| S0 소재 매트릭스 | 채널 × 언어 조합 |
| S1 컴포넌트 슬롯 | 헤드라인/서브/CTA/로고/고지 유무 |
| S2a 비주얼 | image_concept |
| S2b 카피 | copy_themes |
| 다국어 분기 | 다국적 타겟 플래그 + 언어 목록 (Refactor 49줄 트리거) |
| S2b grounding | factsheet(rate/maturity/fee) + 필수 고지 |

→ **Stage B 끝 "계약 검증 게이트"**: 위 스키마 충족 점검, 누락 시 ② AskUser로 되돌려 보충. DesignStudio가 "계획 요소 없음"으로 막히는 것을 원천 차단.

## ① 2-스테이지 워크플로 (요소 1)

| 스테이지 | 모사 대상 | 동작 | 산출 |
|---|---|---|---|
| **Stage A — Brainstorming** | superpowers `brainstorming` | 기획자 페르소나가 멀티턴으로 목표·타겟·메시지·채널·톤 탐색. 리서치 기능(Refactor 41줄)으로 근거 수집·asset 저장, 사용자 수동 asset 추가 허용 | `spec.md` lock |
| **Stage B — Writing-plans** | superpowers `writing-plans` | `spec.md` → AI-optimal 구현계획 변환 + ⓪ 계약 검증 | `plan.md` lock |

- superpowers 원칙 계승: 한 번에 하나 질문(= AskUser 토스트), YAGNI, 발산(A) → 구조화(B).

## ② AskUser 토스트 (요소 2) — bypass (b)

- 미들웨어 웹소켓 리시버(Refactor 44줄) → 클로드 코드 AskUserQuestion처럼 웹에 선택 UI **토스트**.
- **트리거 3종**:
  - (a) 기획 분기 의사결정 — 타겟 우선순위·채널 믹스·톤·다국어 여부 등 모호성 임계 초과.
  - (b) 스테이지 전환 확정 — spec lock / plan lock.
  - (c) 계약 검증 실패 — 누락 요소 보충.
- **bypass = (b) 전부 bypass 가능** (DesignStudio와 동일 정책): BrainStormingStudio Setting에서 트리거 단위 토글. bypass ON 시 해당 분기는 **Marker가 기본값으로 자동 결정**, 산출 완료는 알림으로 통지. (기본값은 모든 토스트 ON 권장.)

## ③ 마케팅물 기획자 페르소나 (요소 4)

- 시스템 프롬프트 = **금융 마케팅 캠페인 기획 전문가**: 타겟 세그멘테이션 · 메시지 전략 · 채널 믹스 · 카피 방향 · 컴플라이언스 인지 · 리서치 기반 의사결정.
- 현재 `brainstorm.py:116`의 "금융상품 디지털 마케팅 기획 어시스턴트"를 전문가 페르소나로 승격.

## ④ 파일시스템 CRUD 스킬 (요소 5 — DesignStudio와 공유)

- 하네스가 가상 폴더 트리에 read/write/update/delete: 리서치 asset 저장, `spec.md`·`plan.md` 생성·갱신, 사용자 추가 asset 읽기.
- **@design_subharness.md ③과 동일 스킬 공유**(같은 인터페이스).
- 백엔드 파일시스템 실체 = **@marker_api.md §3-1 `VfsStore`**(Supabase 백엔드)에서 확정.

## 하네스 6요소 프레임 (디자인 하네스와 대칭)

| 요소 | 내용 |
|---|---|
| 시스템 프롬프트 | 기획자 페르소나(③) |
| 제약/토큰 | factsheet grounding · 컴플라이언스 고지 |
| 레퍼런스 | 리서치 기능(웹/코퍼스) |
| 구조화 출력 | spec.md → plan.md |
| 크리틱/검증 | DesignStudio 계약 검증(⓪) |
| AskUser 훅 | 토스트 UI(②) |
| (+) 공유 스킬 | 파일시스템 CRUD(④) |

## ⑤ 가상 폴더 산출물 구조

> 폴더 트리 SSOT = @vfs.md. 아래는 `/brainstorming/` 발췌.

```
/{runId}/brainstorming/
  assets/
    research/{article,image,video}/   # 자동 수집 (source=research)
    user/{article,image,video}/       # 사용자 수동 추가 (source=user)
  spec.md         # Stage A
  plan.md         # Stage B = DesignStudio 입력 계약
```

- 폴더명은 `brainstorming/`(@vfs.md 정합). 모든 미디어 asset은 sidecar `*.meta.json` 동반.
- `plan.md`를 DesignStudio가 읽어 `/design/` 작업 시작.

## 미결 / 후속 결정 항목

- AskUser 토스트 **모호성 임계 판정 기준**(언제 토스트할지).
- `spec.md` / `plan.md` **섹션 템플릿(스키마)** — ⓪ 계약을 강제하는 구체 양식.
- 리서치 기능 **소스**(웹 검색 vs 내부 코퍼스 vs 혼합).
- 파일시스템 CRUD 스킬 **인터페이스** → @marker_api.md §3-1 `VfsStore`에서 확정(DesignStudio와 공유).
