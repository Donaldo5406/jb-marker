# 가상 폴더 트리 (Virtual File Tree) — VFS SSOT

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" 70줄 "가상 폴더트리 구조 CRUD 방식".
> 위상: brainstorming/design/review 하네스가 공유하는 **상위 SSOT**. @design_subharness.md④·@brainstorm_subharness.md⑤의 폴더 섹션은 이 문서를 참조한다.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app) + docs (01·02 비참조)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화(grounds 방향=P1 이월 명시점, 나머지는 확증 괴리 가산). 점검 보고서 @harness_audit.md

---

## 설계 원칙

1. **run(job) 단위 격리** — 최상위 = `runId`. History·멀티작업·세션 재개의 전제(Refactor 27줄).
2. **스튜디오 = 1급 디렉터리** — STUDIOS = (brainstorming, design, review, deploy, **usage**)(backend/app/vfs/types.py:7 — 경로 검증 대상, vfs/paths.py:21-22). brainstorming/design/review/deploy는 파이프라인 스텝과 1:1. usage는 파이프라인 스텝과 1:1이 아닌 호출 사용량 **집계 뷰**이며 LIFECYCLE_STUDIOS 제외(types.py:9 — 세션 수명주기 비대상, §내부 노드 `_session.json`의 "(usage 제외)" 서술과 정합).
3. **asset 메타 = VfsNode 내장 `meta` dict** — 출처 추적·grounding 인용·검색(backend/app/vfs/types.py:22). grounds도 별도 필드가 아니라 **meta dict의 `grounds` 키**(`meta["grounds"]`)로 기록된다(§노드 메타 스키마). 설계 당시 A안(sidecar `*.meta.json`)이었으나 구현은 노드 내장으로 수렴 — 스토어 레벨 sidecar 파일은 생성되지 않는다(§노드 메타 스키마).
4. **run 메타 = `manifest.json`** — 제목·현재스텝·파이프라인 상태·언어·시각. History·프로세스바(Refactor 30줄)·재개.
5. **design = 단계(rough/final) + design-system(토큰+컴포넌트 카탈로그)** — 컴포넌트를 한 곳에 모아 History 시각화 용이.

## 트리

```
/{runId}/
├── manifest.json                       # run 메타 (History·프로세스바·재개)
├── brainstorming/
│   ├── assets/
│   │   ├── research/                   # 자동 수집 (source=research) — 메타는 노드 내장 meta(sidecar 없음)
│   │   │   └── article/                #   src_{n}.md, meta={source_url,title} — article만 실기록(image/video 미기록)
│   │   └── user/                       # 사용자 수동 추가 — 범용 PUT 관례(미강제, routers/vfs.py:70-72 source=frontend|user)
│   │       ├── article/  image/  video/
│   ├── spec.md                         # Stage A 산출 (grounds=[리서치 citation URL들])
│   └── plan.md                         # Stage B 산출 = design 입력 계약(⓪)
├── design/
│   ├── rough/                          # S1: layout.spec.json + 와이어 미리보기
│   ├── design-system/                  # S2: 토큰 + 컴포넌트 카탈로그 (History 시각화 단위)
│   │   ├── tokens.json                 #   palette·font·grid·aspect
│   │   └── components/
│   │       ├── visual/                 #   2a Gemini 비주얼 (텍스트 free)
│   │       ├── headline/  body/  cta/  #   2b 카피/타이포 컴포넌트
│   │       └── logo/  disclosure/      #   2c 브랜드·AI고지·디스클로저
│   ├── final/                          # S3: 컴포넌트 조립 → 언어별
│   │   ├── ko/   vi/   en/             #   각: main.scene — 작성 주체=프론트 어셈블러(백엔드는 소비자). export(png/mp4) 미구현
│   └── metadata.md                     # ReviewStudio용 텍스트+콘티 메타
├── review/
│   ├── legal/                          # R1 준법: 위반 법률별 포인팅
│   │   ├── law_{id}/                   #   verdict.json (조항·위반위치·근거 봉투)
│   ├── i18n/                           # R2 다국어 동등성: 사유별
│   │   ├── reason_{id}/                #   verdict.json
│   ├── revise/                         # R3 수정 지시 → design 피드백 루프
│   │   ├── image/   text/   video/
│   ├── report.md                       # 검토 종합 (프로세스바·결과)
│   └── (_render/{lang}.png · _state.json — 내부 노드, §내부 노드 표. @review_subharness.md §⑤)
├── deploy/                             # DeployStudio (@deploy_studio.md §5 — 규칙엔진+어댑터)
│   ├── inputs/                         # D0: selected_providers.json · matrix.json
│   ├── eligibility/                    # D1: recipients.json · excluded.json · calendar.json (§50 판정)
│   ├── packages/                       # D2: 채널별 규격 export
│   │   └── {channel}_{lang}/           #   평면 package_id — copy.md · copy.meta.json · package.meta.json
│   ├── advisor/transcripts/            # D2: {package_id}.jsonl — _ 접두 아님 → FileTree 노출(현행 의도)
│   ├── dispatch/                       # D3: plan.json · simulation.json
│   └── report.md                       # D3: 발송계획·시뮬결과·어댑터 상태
└── usage/                              # 집계 뷰 — 파이프라인 스텝과 1:1 아님
    │                                   #   (FileTree에서는 별도 숨김 — frontend/components/cockpit/FileTree.tsx:94-98이
    │                                   #    `_` 접두와 `usage` 세그먼트를 함께 숨김. 비용 표면은 GET /runs/{id}/usage)
    └── log.jsonl                       # TrackedProvider·advisor record_usage 기록처 (observability/usage.py:15-16)
```

## 노드 메타 스키마 (VfsNode 내장 — sidecar 아님)

스토어 레벨 sidecar `*.meta.json` 파일은 생성되지 않는다(설계 당시 A안 → 구현은 노드 내장으로 수렴). meta는 **VfsNode 내장 `meta` dict**(backend/app/vfs/types.py:22) — grounds 데이터도 이 dict의 `grounds` 키로 들어가며, supabase에서는 `vfs_nodes`의 **meta jsonb 컬럼 경유로 영속**된다(vfs/supabase.py:95-101). `VfsNode.grounds` 필드(types.py:23)와 supabase 전용 grounds 컬럼은 **선언만 된 예약 상태** — 채우는 코드가 없어 upsert 시 항상 None(supabase.py:99), 읽기 매핑만 존재(supabase.py:45). 조회 = `read_meta`(vfs/base.py:36). 예외: deploy 라우터만 `*.meta.json` "이름의 일반 텍스트 노드"를 직접 쓴다(라우트 관례 — 스토어 불변식 아님, routers/deploy.py:164-179).

```
공통(노드 필드) = source("research|user|gemini|marker", 라우터 PUT은 frontend|user)
                · mime · hash · created_at · meta
                  # hash·created_at은 meta가 아닌 VfsNode 최상위 필드 (vfs/types.py:24-25)
                  # grounds 필드(types.py:23)는 예약(미사용) — 실데이터는 meta["grounds"]
리서치 asset meta = { "source_url", "title" }                          (harness_brainstorming.py:209-210)
blob 자동 meta   = { "type": "image|video|file", "source", "mime" }    (vfs/local.py:81-83)
                  # 불변식: blob put 시 meta가 비면 자동 기록 (vfs/local.py:79-86)
```

- `origin_url`·`license`·`id`는 미구현 — 예약(미구현).
- **`grounds` = 이 노드(산출물)의 근거 ref** — **기록 위치 = meta dict의 `grounds` 키**(`meta["grounds"]`): 모든 writer가 meta 키로 기록한다(harness_brainstorming.py:250 `meta={"grounds":[...]}`·harness_design.py:384·harness.py:101). `VfsNode.grounds` 필드(types.py:23)와 supabase grounds 컬럼은 **선언만 된 예약 상태**(채우는 코드 없음 — upsert 시 항상 None, supabase.py:99·읽기 매핑만 :45). grounds 데이터의 실제 영속은 **meta jsonb 경유**. P1 이월 명시점: 설계 당시 "이 asset이 근거가 된 산출물 ref"(asset→산출물 정방향)였으나 구현은 방향 역전(산출물→근거).
  - brainstorming `spec.md` put 시 `{grounds: [리서치 citation URL들]}`(gateway/harness_brainstorming.py:249-251).
  - design S2b `layout.spec.json` `{grounds: {corpus: "factsheet", ungrounded: [...]}}`(gateway/harness_design.py:381-385).
  - Passthrough는 `[]`(gateway/harness.py:101).
  - 기록 주체 = 하네스(handle_turn) · 시점 = 산출물 put(gateway/gateway.py:5).
  - 리서치 asset 자체의 출처는 `meta.source_url`로 별도 기록(grounds 키 없음, harness_brainstorming.py:207-210).

## run 메타 스키마 (`manifest.json`)

```
{ "runId",
  "user_id",         # 기본 "demo" — 소유자 격리 키(routers/deps.require_owner 기반), vfs/types.py:29-37
  "title", "created_at", "updated_at",
  "current_step": "brainstorming|design|review|deploy",
  "step_status": { "brainstorming": "...", "design": "...", ... },
  "languages": ["ko","vi","en"] }
```

`list_runs`가 user_id로 필터(vfs/local.py:60-62).

## 스튜디오별 폴더 계약

- **brainstorming** → `spec.md`, `plan.md`, `assets/{research,user}/{article,image,video}/` (메타 = 노드 내장. research는 article만 실기록).
- **design** → `rough/`, `design-system/{tokens.json, components/*}`, `final/{lang}/`, `metadata.md`.
- **review** → `legal/law_*/verdict.json`, `i18n/reason_*/verdict.json`, `revise/{image,text,video}/`, `report.md` (@review_subharness.md §⑤).
- **deploy** → `inputs/`(selected_providers.json·matrix.json) · `eligibility/`(recipients.json·excluded.json·calendar.json — §50 판정) · `packages/{channel}_{lang}/`(**평면** — copy.md·copy.meta.json·package.meta.json) · `advisor/transcripts/{package_id}.jsonl`(**`_` 접두가 아니어서 FileTree에 노출되는 노드 — 현행 의도**) · `dispatch/`(plan.json·simulation.json) · `report.md` (상세 @deploy_studio.md §5).

## CRUD 규약 (공유 스킬 표면 — 실체 = @marker_api.md §3-1)

- 경로 = `/{runId}/{studio}/...`.
- 미디어(blob) put 시 meta가 비면 `{type,source,mime}` **자동 기록** 불변식(vfs/local.py:79-86) — sidecar 파일 생성 없음. 예외: deploy 라우터만 `*.meta.json` 이름의 일반 텍스트 노드를 직접 씀(라우트 관례, routers/deploy.py:164-179).
- 스텝 전환마다 `manifest.json` 갱신 — 불변식: `set_step_status` → `current_step` 자동 동기(vfs/local.py:49-58·supabase.py:67-76).

## 내부 노드 (`_`-접두 — FileTree 숨김(+usage 스튜디오))

스튜디오 네임스페이스 `/{runId}/{studio}/` 아래 `_` 접두 노드는 하네스/세션 내부 상태로, History FileTree에 노출하지 않는다.

| 노드 | 책임 |
|---|---|
| `_state.json` | 하네스 무상태 재개용 스냅샷 (하네스 소유). `version: 1` 규약 — gateway/state.py 공용 load_state/save_state(STATE_VERSION=1 :12, state_path=`/{run_id}/{studio}/_state.json` :15-16, save 시 version setdefault·source=marker·mime=json :27-30, 레거시 run은 다음 저장에서 백필). design은 `gate`(None\|step) 필드로 confirm 게이트 정지 지점을 보존 — gate-ON 단계는 생성 후 정지(rail confirm), bypass 단계는 한 턴 내 critic/grounding 통과 시 연쇄. spec `2026-06-01-design-confirm-gate-o2-design.md` §3.2. |
| `_messages.json` | 턴 메시지 영속 (하네스 소유) — 현재 brainstorming 전용. |
| `_material_matrix.json` | design **S0** 소재 매트릭스 — S0 setup에서 plan.md frontmatter로부터 추출해 기록(gateway/harness_design.py:492-519, put :517 — design_subharness.md:114와 정합). |
| `_render/{lang}.png` | review — **프론트 업로드** 합성 렌더(R1 비전 입력). R0 cleanup 보존 대상 (gateway/harness_review.py:128·155). |
| `_passthrough.md` | 공통 Passthrough 산출 — FileTree 숨김 (gateway/harness.py:107-109). |
| `_session.json` | 세션 수명주기 봉투 — created/updated/status(active·suspended·archived)·suspended_at·last_activity_kind. lazy heartbeat 2단계(active→suspended 60m→archived +7d). spec `2026-06-01-studio-session-lifecycle-policy-design.md` §3. 대상 스튜디오 = brainstorming/design/review/deploy(usage 제외). |

## 미결 / 후속 결정 항목

- ~~파일시스템 CRUD 스킬 **인터페이스** + **저장 매개체**~~ → @marker_api.md 에서 확정(VfsStore 추상화 + Supabase Postgres/Storage, AI 게이트웨이).
- ~~`deploy/` **내부 구조**~~ → @deploy_studio.md §5 에서 확정.
- revise 반복 시 design **버전닝/이력** 방식 (@marker_api.md §미결과 연결).
