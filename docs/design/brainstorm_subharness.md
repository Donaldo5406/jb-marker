# Marker BrainStorming 하네스 설계 (Brainstorm Sub-harness)

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" — Marker 모델(브레인스토밍) 하네스(67줄).
> 짝 문서: @design_subharness.md(DesignStudio). 공유 요소: 파일시스템 CRUD 스킬.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app) + docs (01·02 비참조)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화. 점검 보고서 @harness_audit.md

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

→ **검증은 두 겹**(구현): (1) **Stage B 매 턴** critic(plan_md)이 `REQUIRED_PLAN_FIELDS` 9키의 frontmatter 누락을 검사 → 누락 시 ② AskUser trigger (c)로 보충(harness_brainstorming.py:342-351 — 'Stage B 끝 1회'가 아니라 매 턴). (2) **Stage A 충분성 게이트 `critic_spec`**(`REQUIRED_SPEC_FIELDS` 9키, :24-34) — LLM이 ready=true여도 누락 시 확정(b) 대신 보충(c)을 띄운다(:258-268). 두 critic의 출력은 `CriticVerdict` 봉투(gateway/critic.py:5-21). DesignStudio가 "계획 요소 없음"으로 막히는 것을 원천 차단.

## ① 2-스테이지 워크플로 (요소 1)

| 스테이지 | 모사 대상 | 동작 | 산출 |
|---|---|---|---|
| **Stage A — Brainstorming** | superpowers `brainstorming` | 기획자 페르소나가 멀티턴으로 목표·타겟·메시지·채널·톤 탐색. 리서치 기능(Refactor 41줄)으로 근거 수집·asset 저장, 사용자 수동 asset 추가 허용. ready 시 **충분성 게이트 `critic_spec`** 통과 후에만 확정(b) (⓪) | `spec.md` lock |
| **Stage B — Writing-plans** | superpowers `writing-plans` | `spec.md` → AI-optimal 구현계획 변환 + **매 턴** ⓪ 계약 critic | `plan.md` lock |

- superpowers 원칙 계승: 한 번에 하나 질문(= AskUser 토스트), YAGNI, 발산(A) → 구조화(B).
- 멀티턴 컨텍스트는 O4 컴팩션으로 관리 — 직전 input_tokens > COMPACT_INPUT_TOKENS(100k) 시 오래된 턴을 증분 요약으로 접고 최근 KEEP_RECENT(8)개만 원문 전달(harness_brainstorming.py:17-22·:160-201).

## ② AskUser 토스트 (요소 2)

- AskUser 게이트 = `GateEnvelope(kind="ask", trigger="a|b|c", question, options, actions=["answer"])` — `_to_gate`(harness_brainstorming.py:74-81). WS로 `{type:"gate", gate:{...}}` 송출(:276 Stage A·:359 Stage B)되고 HTTP 응답의 `gate` 필드에도 동시 탑재(:278·:361). 회신은 POST /gateway/run body의 `answer` 필드. 프론트는 `applyGate` 단일 적용점에서 kind="ask" → `pendingGate`로 보관(AskUserToast가 소비). 상세 @ws_protocol.md.
- **트리거 3종**:
  - (a) 기획 분기 의사결정 — 타겟 우선순위·채널 믹스·톤·다국어 여부 등 모호성 임계 초과.
  - (b) 스테이지 전환 확정 — spec lock / plan lock.
  - (c) 계약 검증 실패 — 누락 요소 보충.
- 브레인스토밍 게이트는 **bypass 불가** — 모든 spec/plan 확정은 충분성·계약 critic + 사람 confirm(ask trigger b)을 반드시 거친다(harness_brainstorming.py:258-259 주석 'bypass 경로는 제거됨'). `HarnessRequest.bypass_map`은 design 전용(harness.py:25 주석·소비처 harness_design.py:163-164). (설계 당시 bypass 허용안은 구현에서 제거됨.)

## ③ 마케팅물 기획자 페르소나 (요소 4)

- 시스템 프롬프트 = **금융 마케팅 캠페인 기획 전문가**: 타겟 세그멘테이션 · 메시지 전략 · 채널 믹스 · 카피 방향 · 컴플라이언스 인지 · 리서치 기반 의사결정.
- **구현 완료** — `PERSONA` 상수(harness_brainstorming.py:40-44)가 `PromptSpec.persona`로 주입(:229-233 Stage A·:316-324 Stage B). (과거 mvp/03 `brainstorm.py`의 "기획 어시스턴트"를 전문가 페르소나로 승격한 결과 — 구 파일은 현 레포에 없음.)

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
| AskUser 훅 | `GateEnvelope(kind="ask")` 봉투 → WS+HTTP 동시 전달 → AskUserToast UI(② — @ws_protocol.md) |
| (+) 공유 스킬 | 파일시스템 CRUD(④) |

## ⑤ 가상 폴더 산출물 구조

> 폴더 트리 SSOT = @vfs.md. 아래는 `/brainstorming/` 발췌.

```
/{runId}/brainstorming/
  _messages.json  # 멀티턴 대화 영속 (harness_brainstorming.py:132-140)
  _state.json     # stage·compaction 상태, version:1 (gateway/state.py:15-16·:27-30)
  assets/
    research/article/src_{n}.md       # 자동 수집 — 웹검색 citations 영속 (source=research, :203-211)
    research/{image,video}/           # 관례 예약 (미구현)
    user/{article,image,video}/       # 사용자 수동 추가 (source=user)
  spec.md         # Stage A — meta.grounds = 리서치 citation URL (P1 이행, :249-251)
  plan.md         # Stage B = DesignStudio 입력 계약
```

- 언더스코어(`_`) 접두 = 내부 노드 — 프론트 파일트리에서 숨김.
- 폴더명은 `brainstorming/`(@vfs.md 정합). asset의 meta는 **노드 내장 `meta` dict**(`read_meta`로 조회 — vfs/base.py:36) — sidecar `*.meta.json` 파일이 아님(구 서술 교정).
- `plan.md`를 DesignStudio가 읽어 `/design/` 작업 시작.

## 미결 / 후속 결정 항목 — 해소 현황

- ~~`spec.md` / `plan.md` 섹션 템플릿(스키마)~~ → **확정**: YAML frontmatter 필수키 셋(`REQUIRED_SPEC_FIELDS`·`REQUIRED_PLAN_FIELDS` 각 9키, harness_brainstorming.py:24-34)으로 ⓪ 계약 강제.
- ~~리서치 기능 소스~~ → **확정**: provider-native 웹검색(`WEB_SEARCH_TOOL` :36-38, Stage A에서 `tools=` 전달 :234-236) + citations 영속(`_save_research`).
- ~~파일시스템 CRUD 스킬 인터페이스~~ → **확정**: `VfsStore` ABC(`put_text`/`get_text` 포함 — @marker_api.md §3-1, DesignStudio와 공유).
- AskUser 토스트 **모호성 임계 판정 기준** → **LLM 자율 판단**(프로토콜 `ask` 필드, :46-52)으로 정착.
