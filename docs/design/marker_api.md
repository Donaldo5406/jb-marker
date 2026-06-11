# Marker API & VFS 저장 매개체 설계 (Storage Medium + CRUD/AI Gateway)

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" 70줄(가상 폴더트리 CRUD) + `front → API → vfs & AI API` 구조.
> 위상: @vfs.md 후속 — @vfs.md가 남긴 "저장 매개체"·"CRUD 스킬 인터페이스" 미결을 확정한다.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app) + docs (01·02 비참조)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화. 점검 보고서 @harness_audit.md

---

## 0. 결정 요약

- **저장 매개체** = `VfsStore` 추상화 **계층** 위에 **Supabase**(Postgres + Storage) 무료 영속 백엔드.
  - 기본 impl = `LocalVfsStore`(테스트 · 오프라인 데모) / 라이브 impl = `SupabaseVfsStore` — `vfs/factory.py:11-19` `VFS_BACKEND` 스위치. 추상화라 벤더 스왑 자유(락인 없음).
- **Marker API** = 백엔드 게이트웨이의 두 책임. 실체 = `server.py` 조립 전용 팩토리(102줄 — app.state 5종: settings·store·session_store·connections·gateway) + `routers/` 8모듈(§3):
  1. **내부 VFS CRUD** — `VfsStore` 인프로세스 인터페이스(3 하네스 공유 스킬의 실체).
  2. **AI 게이트웨이** — `MarkerGateway` = 엔타이틀먼트 choke + provider 팩토리/래핑 + 하네스 위임(`gateway/gateway.py:28-34` — put 호출 없음). **VFS 영속(+`meta.grounds`)은 하네스(`handle_turn`) 책임**(`gateway.py:3-6` docstring).
- **오케스트레이션** = **LangGraph 미사용**. 상태의 유일한 주인은 Supabase, 진행은 사용자 네비게이션, 스튜디오는 에이전트 루프(클로드 코드식). → §2.

---

## 1. 저장 매개체 (Q1 결정)

### 휘발성 진단 (과거 mvp/03 기준 — 이행 완료)
> 아래 진단은 과거 mvp/03-marketing 코드 기준 기록이며, jb-marker 이행으로 전부 해소됐다(인용했던 `graph.py`·`storage.py` 등은 현 레포 부재). 현행 영속 = `VfsStore`(`LocalVfsStore`/`SupabaseVfsStore`, `vfs/factory.py:11-19` `VFS_BACKEND` 스위치), LangGraph는 import 자체 없음.
- 런 상태: `RUNS: dict` 인메모리 + LangGraph **SqliteSaver가 `:memory:`** → 재시작 시 소멸.
- 블롭(PNG): 로컬 디스크 `data/runs/<run_id>/<asset_id>.png`, "HF Space ephemeral filesystem 호환" = 휘발 감수. 이미 runId 격리.
- `DATABASE_URL=sqlite:///marketing.db`: 어디에도 배선 안 된 **죽은 설정**.
- → 안정적 데모(History·세션 재개)에 필요한 **영속이 전무** → 아래 결정(Supabase)으로 해소.

### 결정: 추상화 위 무료 영속 DB (Supabase)
데이터 2형상을 분리 저장하되 **하나의 논리경로**(`/{runId}/{studio}/...`)로 추상화.

| 형상 | 대상 | 매개체 |
|---|---|---|
| 구조/텍스트 | `manifest`, `spec.md`, `plan.md`, `*.meta.json`, `tokens.json`, `report.md` | **Supabase Postgres** |
| 블롭 | visual PNG, `*.scene`, export png/mp4 | **Supabase Storage 버킷** (서빙은 `GET /vfs/{run_id}/{rest:path}` 바이너리 분기 — §3-3. public/signed URL 직링크는 미채택) |

### 스키마 스케치 (논리 트리 ↔ 관계형 매핑)
```
runs                         # manifest.json 승격 → History 목록·필터·재개
  run_id PK, user_id, title, current_step,   # user_id = Supabase Auth 소유자(Refactor C1)
  step_status jsonb, languages[], created_at, updated_at

vfs_nodes                    # 트리의 모든 파일/노드
  (run_id, path) PK,         #   path = /{runId}/{studio}/...
  kind, mime, source,        #   source: research|user|gemini|marker
  content_text?,             #   md/json 텍스트 (블롭이면 null)
  blob_path?,                #   Storage 객체 키 (텍스트면 null)
  meta jsonb,                #   ← sidecar *.meta.json 을 컬럼으로 흡수
  grounds?, hash, created_at #   grounds 컬럼 = 예약(미사용) — 실데이터는 meta.grounds 키(@vfs.md 메타 스키마)
```
- **sidecar `*.meta.json` → `meta jsonb` 컬럼으로 흡수**: 별도 파일 불필요, 논리경로엔 여전히 `*.meta.json`로 노출 가능. @vfs.md 메타 스키마 그대로.
- **`manifest.json` → `runs` 테이블 row**: History 전체 목록·상태 필터·재개가 쿼리로 즉시(파일 스캔 불요).

### 무료 근거 + 대안
- Supabase free: Postgres 500MB + Storage 1GB. 비활성 1주 일시정지 caveat → 핑/keep-alive로 회피(데모 허용 범위).
- 대안(추상화라 스왑 가능): **Turso(libSQL)** = 과거 03 SqliteSaver 연속성 + **R2** 무료 블롭(2벤더) / **Neon** PG(블롭 별도).

### 관련 구조점 — 단일 상태원천
- Supabase가 상태의 주인이 되면 별도 세이브 장치(LangGraph checkpointer)가 **불필요**해진다 — manifest(`runs`) + VFS(`vfs_nodes`) + 블롭(Storage) **한 substrate**가 라이브 진행 상태까지 담는다.
- → 오케스트레이션에서 LangGraph를 제거하는 근거. 상세 §2.

---

## 2. 오케스트레이션 — LangGraph 미사용

JB Marker는 기존 03의 LangGraph(StateGraph + SqliteSaver)를 **쓰지 않는다.** 상태의 유일한 주인은 Supabase, 진행은 사용자 네비게이션, 각 스튜디오는 에이전트 루프다 — 클로드 코드와 동일한 "에이전트 루프 + 도구 + 영속 상태" 구조(DAG 엔진 없음).

### LangGraph가 하던 3가지 → 대체물

| LangGraph 역할 (03) | JB Marker 대체 |
|---|---|
| 단계 자동 연결(DAG 진행) | **사용자 수동 네비게이션**(@navigate.md) + `runs.step_status`. 스튜디오는 자동 연결이 아니라 사용자가 트리거 |
| 갈림길 자동 판단(조건부 라우팅·게이트) | **`step_status` 값 + 게이트 봉투.** 별도 confirm/approve 엔드포인트 없음 — `POST /gateway/run` 단일 + 응답 `gate`(GateEnvelope kind/actions), 게이트 회신은 `action`(Literal 5종 advance·confirm·regenerate·restart·ack, `routers/gateway.py:38`). critical→`BLOCKED` 기록 → 프론트가 다음 탭 잠금(@navigate.md③ · @review_subharness.md 게이트) |
| 세이브·이어하기(checkpointer interrupt/resume) | **상태가 이미 Supabase(manifest+VFS)에 영속.** 이어하기=manifest 읽고 그 지점부터 속행. 멈춤(interrupt)=AskUser 질문을 GateEnvelope kind="ask"(WS `{type:"gate"}`)로 내보내고 대기, 회신은 다음 `POST /gateway/run`의 `answer` 필드(`routers/gateway.py:33·:37`) — 상세 @ws_protocol.md |

### 왜 안 써도 되나 (근거)

1. **상태가 이미 영속** — §1에서 Supabase가 상태의 주인이 됨 → LangGraph의 존재 이유(checkpoint/resume)가 Supabase로 흡수. checkpointer를 또 두면 **두 상태원천**이 됨.
2. **이중 상태 동기화 고통 소멸** — 과거 mvp/03 `server.py`는 `RUNS`(메모리)와 checkpointer를 수동 동기화하느라 주석이 도배돼 있었고, 이 동기화 실수로 imaging 429 폭주 회귀까지 있었다(과거 코드 기준 기록 — 현 레포 부재). 단일 상태원천이면 이 버그 클래스가 통째로 사라짐.
3. **하네스는 DAG가 아니라 에이전트 루프** — 멀티턴·AskUser(GateEnvelope kind="ask")·도구 호출(@brainstorm_subharness.md①② · @design_subharness.md③)은 순서도 노드가 아니라 클로드 코드식 루프. 그래프 노드에 끼우면 어색.
4. **진행이 수동** — @navigate.md 모델 C에서 스튜디오 이동은 사용자 클릭. 자동 라우팅 엔진 불요.

### 대체 오케스트레이션 (구조)

- **스튜디오 내부** = 하네스 **에이전트 루프**: 시스템프롬프트+제약을 씌운 Claude/Gemini 호출 ↔ `VfsStore` CRUD(도구) ↔ AskUser(GateEnvelope kind="ask", WS `{type:"gate"}` — @ws_protocol.md) 반복 → 산출물 VFS 영속.
- **스튜디오 사이** = API 엔드포인트 + `runs.step_status`: 스튜디오 종료 시 산출물 + `step_status` 갱신, 다음 스튜디오는 사용자가 트리거(@navigate.md).
- **게이트·재개** = `step_status` 값 + GateEnvelope: 별도 confirm/approve 엔드포인트 없음 — `POST /gateway/run` 단일, 게이트 회신은 `action`·`answer` 필드. checkpointer 대신 **Supabase 읽기/쓰기**.
- (이행 결과) 과거 03 노드 로직(`brainstorm`/`generate`/`review`/`i18n_equiv`) 재사용 계획은 **하네스 3종**(`harness_brainstorming`·`harness_design`·`harness_review`) + `registry.select_harness`(`gateway/registry.py:15`)로 실현 — `graph.py`는 현 레포에 존재하지 않는다.

---

## 3. Marker API (Q2 결정)

`front → API → (vfs | AI)`. API = `server.py` 조립 전용 팩토리(102줄 — app.state 5종: settings·store·session_store·connections·gateway) + `routers/` 8모듈(meta·runs·gateway·session·vfs·deploy·observability·history = swagger 태그 1:1, openapi_tags·version 0.4.0 `server.py:26-41`). 게이트웨이 실체 = `MarkerGateway`(`gateway/gateway.py:18-34`, `app.state.gateway` 주입 `server.py:92-95`).

### 3-1. 내부 VFS CRUD — 공유 스킬의 실체
- `VfsStore` **인프로세스 파이썬 인터페이스** = @brainstorm_subharness.md④ · @design_subharness.md③ · @review_subharness.md④ 가 공유하는 "파일시스템 CRUD 스킬"의 **실체**. (하네스는 자기 서버를 HTTP로 호출하지 않음.)
- 표면(논리경로 `/{runId}/{studio}/...`) — 메서드명·시그니처는 `vfs/base.py` ABC와 1:1(`base.py:1`이 이 표를 계약 출처로 역참조):

| 연산 | 의미 |
|---|---|
| `put(path, content, *, meta=None, source=None, mime=None)` | 텍스트→Postgres row, 블롭→Storage 업로드+row |
| `get(path)` / `read_meta(path)` | 콘텐츠 / 메타 조회 |
| `list(prefix)` | 트리·History 열거 |
| `update(path, patch)` / `delete(path)` | 갱신 / 삭제 |
| `put_text(path, content, *, source=None, mime=None)` / `get_text(path)` | 텍스트 편의 — Local/Supabase 중복 구현을 ABC 구체 메서드로 승격(T1-P1, `base.py:47-55`). deploy 라우트·DeployAdvisor·usage 로그의 정식 표면 |
| `create_run(run_id, *, user_id="demo", title=None, languages=None)` / `list_runs(*, user_id="demo")` | run 생성 / 사용자별 run 목록 |
| `get_manifest(run_id)` / `patch_manifest(run_id, patch)` / `set_step_status(run_id, step, status)` | run 메타. **스텝 전환 → `runs` row 갱신(불변식)** |

- 불변식(@vfs.md CRUD 규약): ① blob `put` 시 `meta` 자동 기록(`vfs/local.py:79-86` — 스토어 구현 불변식)·그 외 `meta`는 하네스가 명시 전달하는 규약, ② 스텝 전환 → manifest 갱신(`set_step_status`).

### 3-2. AI 게이트웨이 — request 하네스 적용 / response 서빙
사용자 결정의 핵심. 모든 AI 프로바이더 호출이 이 경유를 거친다.

- **request 하네스 적용**: 6요소는 **PromptSpec**(`gateway/prompt.py` — persona·constraints·references·output_schema + studio/step 신호, `assemble()` 결정론 조립) + **CriticVerdict**(`gateway/critic.py`) + **GateEnvelope**(AskUser 훅 = kind="ask")로 실체화. Harness ABC = `handle_turn`(필수) + `output_path` + (선택) `system_prompt`(`gateway/harness.py:71-77`). studio/step 신호는 `Provider.complete(meta=)` 경유 전달(DemoProvider 단계 감지).
- **프로바이더**: Literal 5종 `anthropic`·`openai`·`google`·`fake`·`demo`(`routers/gateway.py:30-31`). IMG.LY는 백엔드 프로바이더가 아님(프론트 에디터 영역 — 현 구현은 Fabric.js). 미디어 provider(`google`, mock 시 `demo`)는 `tracked_provider` 래핑으로 usage 기록(`routers/gateway.py:68-76`·`providers/wrappers.py`).
- **raw 프롬프트 직행 금지** — 게이트웨이 경유 강제로 **구현됨**(`gateway/gateway.py` docstring "raw 프롬프트 직행 금지: 항상 하네스(최소 Passthrough) + 게이트웨이 경유"). 과거 mvp/03의 조잡함(`prompt_builder.py` 단일샷)은 이렇게 원천 차단됐다.
- **response 서빙·영속 책임**: 게이트웨이 = 엔타이틀먼트 choke + provider 팩토리/래핑 + 하네스 위임(`gateway/gateway.py:28-34` — put 호출 없음). **VFS 영속(+`meta.grounds`)은 하네스(`handle_turn`) 책임**(`gateway.py:3-6` docstring). 프론트 서빙 = REST 응답 4키 `{output_path, text, gate, meta}`(`routers/gateway.py:93-95`) + WS 이벤트 3종 artifact/gate/session(`_publish` 현행 위치 `routers/gateway.py:47-52`) — WS 단일 레퍼런스 @ws_protocol.md.
- **`meta.grounds` 기록 — 이행 완료**. 기록 지점 3곳: Passthrough `grounds: []`(`gateway/harness.py:101`) · brainstorming 리서치 citation(`harness_brainstorming.py:249-251`) · design S2b `{corpus:"factsheet", ungrounded:[...]}`(`harness_design.py:381-385`). grounds는 **meta jsonb로 영속**(전용 `grounds` 컬럼은 예약 상태 — 채우는 코드 없어 upsert 시 항상 None, `vfs/supabase.py:99`).
- 원칙: **AI 산출물은 항상 VFS를 경유해 서빙** → grounding·메타·History가 자동으로 따라붙음.
- **엔타이틀먼트 게이트**(Refactor C4): Marker 하네스 · DeployStudio 어드바이저 호출은 **유료 티어($100/월)** 전용(무료 = raw Claude/GPT/Gemini만). 판정 함수 = `app/entitlement.py` `is_entitled(user_id)`(`:28-36`, env override OR store) **단일 choke**. 소비자 5곳: gateway 배선(`server.py:93`)·advisor chat(`routers/deploy.py:191`)·dispatch(`:222`)·GET/PUT `/entitlement`(`routers/meta.py:27·38`)·deploy `_state`(`:311`). `check()`(`:39-41`)는 store 단독 판정 — 신규 사용 금지 주석. 모델 선택은 Claude/GPT/Gemini 공통 지원(C2).

### 3-3. 프론트 표면 (얇게)
- 런 트리거: `/run` 엔드포인트 없음 — `POST /runs`(생성)·`GET /runs`(목록, `routers/runs.py:20·30`)·`POST /gateway/run`(하네스 1턴, `routers/gateway.py:55`).
- VFS read: `list`/`get` (History · 파일브라우저 · 에디터 로드).
- VFS save: 에디터 scene 편집 → `put` (에디터 오버레이 저장 — 현 구현 Fabric.js, Refactor 51줄).
- asset 서빙: `/assets` 라우트 없음. 블롭 서빙 = `GET /vfs/{run_id}/{rest:path}`의 바이너리 분기(`routers/vfs.py:49-51`, OpenAPI 다형 명시 `:40-42`). "Storage public/signed URL 직링크" 대안은 미채택. WS 이벤트 3종 artifact/gate/session — 단일 레퍼런스 @ws_protocol.md.
- 전체 HTTP 표면(session·observability·history·deploy 포함)은 `/docs`(OpenAPI 0.4.0)·태그 8종 — 라우트 정본은 `backend/app/routers/`.

---

## 4. 기존 자산 재사용 / 변경점 (과거 mvp/03 기준 진단 — 이행 완료)

> 과거 mvp/03 코드 기준 이행 계획 기록이며 전부 이행 완료(인용했던 `storage.py`·`graph.py`는 현 레포 부재).
- **재사용한 것**: run_id 스코프 · WS `_publish` 패턴(현행 `routers/gateway.py:47-52`) · artifact 이벤트.
- **변경 완료**: 로컬 PNG write → `VfsStore.put`(블롭) / 인메모리 휘발 → `VfsStore` 영속(`LocalVfsStore`/`SupabaseVfsStore`, `vfs/factory.py:11-19` `VFS_BACKEND` 스위치) / 죽은 `DATABASE_URL` 제거 / LangGraph 그래프 배선 제거 — 현 레포는 LangGraph import 자체 없음(§2).

---

## 미결 / 후속 결정 항목

해소된 항목(기록 보존):
- ~~03 `graph.py` 그래프 배선 제거 + 노드 로직을 평범한 함수로 재사용~~ — **해소**: `graph.py` 부재. 스튜디오는 하네스 3종 + `registry.select_harness`(`gateway/registry.py:15`) 구조(§2).
- ~~`VfsStore` 논리경로 ↔ (`runs`/`vfs_nodes`) 매핑 규격 상세~~ — **구현됨**: `vfs/supabase.py` — `runs`/`vfs_nodes` 테이블 + Storage 블롭, `grounds`·`hash`·`blob_path`·`meta` 컬럼.
- ~~오프라인/테스트 impl ↔ 라이브 impl 동등성 계약~~ — 공유 ABC(`vfs/base.py`) + 공용 테스트로 담보. 현행 백엔드 **523 passed**(P4 머지 기준).

잔존 미결:
- Supabase free **일시정지 대응**(핑/keep-alive 주기).
- 블롭 서빙: Storage **public 버킷 vs signed URL**(접근제어) — 현행은 `/vfs` 경유 서빙(§3-3), 직링크 미채택.
- revise **버전닝/이력**(@vfs.md 미결과 연결).
