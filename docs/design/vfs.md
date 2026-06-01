# 가상 폴더 트리 (Virtual File Tree) — VFS SSOT

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" 70줄 "가상 폴더트리 구조 CRUD 방식".
> 위상: brainstorming/design/review 하네스가 공유하는 **상위 SSOT**. @design_subharness.md④·@brainstorm_subharness.md⑤의 폴더 섹션은 이 문서를 참조한다.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 (01·02 비참조)

---

## 설계 원칙

1. **run(job) 단위 격리** — 최상위 = `runId`. History·멀티작업·세션 재개의 전제(Refactor 27줄).
2. **스튜디오 = 1급 디렉터리** — brainstorming/design/review/deploy, 파이프라인 스텝과 1:1.
3. **asset 메타 = sidecar `*.meta.json`** (A안) — 출처 추적·grounding 인용·라이선스·검색.
4. **run 메타 = `manifest.json`** — 제목·현재스텝·파이프라인 상태·언어·시각. History·프로세스바(Refactor 30줄)·재개.
5. **design = 단계(rough/final) + design-system(토큰+컴포넌트 카탈로그)** — 컴포넌트를 한 곳에 모아 History 시각화 용이.

## 트리

```
/{runId}/
├── manifest.json                       # run 메타 (History·프로세스바·재개)
├── brainstorming/
│   ├── assets/
│   │   ├── research/                   # 자동 수집 (source=research)
│   │   │   ├── article/                #   a1.html + a1.meta.json (sidecar)
│   │   │   ├── image/                  #   + .meta.json
│   │   │   └── video/
│   │   └── user/                       # 사용자 수동 추가 (source=user)
│   │       ├── article/  image/  video/   #   각 + .meta.json
│   ├── spec.md                         # Stage A 산출
│   └── plan.md                         # Stage B 산출 = design 입력 계약(⓪)
├── design/
│   ├── rough/                          # S1: layout.spec.json + 와이어 미리보기
│   ├── design-system/                  # S2: 토큰 + 컴포넌트 카탈로그 (History 시각화 단위)
│   │   ├── tokens.json                 #   palette·font·grid·aspect
│   │   └── components/
│   │       ├── visual/                 #   2a Gemini 비주얼 (텍스트 free) + .meta.json
│   │       ├── headline/  body/  cta/  #   2b 카피/타이포 컴포넌트
│   │       └── logo/  disclosure/      #   2c 브랜드·AI고지·디스클로저
│   ├── final/                          # S3: 컴포넌트 조립 → 언어별
│   │   ├── ko/   vi/   en/             #   각: *.scene + export(png/mp4)
│   └── metadata.md                     # ReviewStudio용 텍스트+콘티 메타
├── review/
│   ├── legal/                          # 준법: 위반 법률별 포인팅
│   │   ├── law_1922/   law_5321/       #   각: 조항·위반위치·근거
│   ├── i18n/                           # 다국어 동등성: 사유별
│   │   ├── reason_001/   reason_002/
│   ├── revise/                         # 수정 지시 → design 피드백 루프
│   │   ├── image/   video/
│   └── report.md                       # 검토 종합 (프로세스바·결과)
└── deploy/                             # DeployStudio (@deploy_studio.md — 규칙엔진+어댑터)
    ├── eligibility/                    # D1: §50 판정(발송대상·제외+법인용·24h 캘린더)
    ├── packages/                       # D2: 채널별 규격 export
    │   └── {channel}/{lang}/           #   이메일/인스타/알림톡/배너 × 언어 + 발송메타
    └── report.md                       # D3: 발송계획·시뮬결과·어댑터 상태
```

## sidecar 메타 스키마 (`*.meta.json`)

```
{ "id", "type": "article|image|video|scene|export",
  "mime", "source": "research|user|gemini|marker",
  "origin_url"?, "license"?,
  "grounds"?,        # 이 asset이 근거가 된 산출물 ref (grounding 인용 추적)
  "created_at", "hash" }
```

## run 메타 스키마 (`manifest.json`)

```
{ "runId", "title", "created_at", "updated_at",
  "current_step": "brainstorming|design|review|deploy",
  "step_status": { "brainstorming": "...", "design": "...", ... },
  "languages": ["ko","vi","en"] }
```

## 스튜디오별 폴더 계약

- **brainstorming** → `spec.md`, `plan.md`, `assets/{research,user}/{article,image,video}/` (+ sidecar).
- **design** → `rough/`, `design-system/{tokens.json, components/*}`, `final/{lang}/`, `metadata.md`.
- **review** → `legal/law_*`, `i18n/reason_*`, `revise/{image,video}`, `report.md`.
- **deploy** → `eligibility/`(§50 판정), `packages/{channel}/{lang}/`, `report.md` (@deploy_studio.md).

## CRUD 규약 (공유 스킬 표면 — 실체 = @marker_api.md §3-1)

- 경로 = `/{runId}/{studio}/...`.
- 미디어 write 시 sidecar `*.meta.json` **동시 생성**.
- 스텝 전환마다 `manifest.json` 갱신.

## 내부 노드 (`_`-접두 — FileTree 숨김)

스튜디오 네임스페이스 `/{runId}/{studio}/` 아래 `_` 접두 노드는 하네스/세션 내부 상태로, History FileTree에 노출하지 않는다.

| 노드 | 책임 |
|---|---|
| `_state.json` | 하네스 무상태 재개용 스냅샷 (하네스 소유). design은 `gate`(None\|step) 필드로 confirm 게이트 정지 지점을 보존 — gate-ON 단계는 생성 후 정지(rail confirm), bypass 단계는 한 턴 내 critic/grounding 통과 시 연쇄. spec `2026-06-01-design-confirm-gate-o2-design.md` §3.2. |
| `_messages.json` | 턴 메시지 영속 (하네스 소유). |
| `_session.json` | 세션 수명주기 봉투 — created/updated/status(active·suspended·archived)·suspended_at·last_activity_kind. lazy heartbeat 2단계(active→suspended 60m→archived +7d). spec `2026-06-01-studio-session-lifecycle-policy-design.md` §3. 대상 스튜디오 = brainstorming/design/review/deploy(usage 제외). |

## 미결 / 후속 결정 항목

- ~~파일시스템 CRUD 스킬 **인터페이스** + **저장 매개체**~~ → @marker_api.md 에서 확정(VfsStore 추상화 + Supabase Postgres/Storage, AI 게이트웨이).
- ~~`deploy/` **내부 구조**~~ → @deploy_studio.md §5 에서 확정.
- revise 반복 시 design **버전닝/이력** 방식 (@marker_api.md §미결과 연결).
