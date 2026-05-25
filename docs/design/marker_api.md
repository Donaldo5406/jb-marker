# Marker API & VFS 저장 매개체 설계 (Storage Medium + CRUD/AI Gateway)

> 대상: @Refactor.md §"백에서 정의되어야 하는 기획" 70줄(가상 폴더트리 CRUD) + `front → API → vfs & AI API` 구조.
> 위상: @vfs.md 후속 — @vfs.md가 남긴 "저장 매개체"·"CRUD 스킬 인터페이스" 미결을 확정한다.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 (01·02 비참조)

---

## 0. 결정 요약

- **저장 매개체** = `VfsStore` 추상화 **계층** 위에 **Supabase**(Postgres + Storage) 무료 영속 백엔드.
  - 기본 impl = 로컬/인메모리(현 `storage.py` 패턴 · 테스트 · 오프라인 데모).
  - 라이브 impl = Supabase. 추상화라 벤더 스왑 자유(락인 없음).
- **Marker API** = 백엔드 게이트웨이(`server.py` FastAPI 확장)의 두 책임:
  1. **내부 VFS CRUD** — `VfsStore` 인프로세스 인터페이스(3 하네스 공유 스킬의 실체).
  2. **AI 게이트웨이** — request에 **하네스 적용** → 프로바이더 호출 → response **VFS 영속 + 서빙**.
- **오케스트레이션** = **LangGraph 미사용**. 상태의 유일한 주인은 Supabase, 진행은 사용자 네비게이션, 스튜디오는 에이전트 루프(클로드 코드식). → §2.

---

## 1. 저장 매개체 (Q1 결정)

### 현행 휘발성 진단 (코드 근거)
- 런 상태: `RUNS: dict` 인메모리(`server.py:91` "no persistence, MVP scope") + LangGraph **SqliteSaver가 `:memory:`**(`graph.py:478`) → 재시작 시 소멸.
- 블롭(PNG): `data/runs/<run_id>/<asset_id>.png`(`storage.py`), 주석 "HF Space ephemeral filesystem 호환" = 휘발 감수. 이미 runId 격리.
- `DATABASE_URL=sqlite:///marketing.db`(`config.py`): 어디에도 배선 안 됨 — **죽은 설정**.
- → 안정적 데모(History·세션 재개)에 필요한 **영속이 전무**.

### 결정: 추상화 위 무료 영속 DB (Supabase)
데이터 2형상을 분리 저장하되 **하나의 논리경로**(`/{runId}/{studio}/...`)로 추상화.

| 형상 | 대상 | 매개체 |
|---|---|---|
| 구조/텍스트 | `manifest`, `spec.md`, `plan.md`, `*.meta.json`, `tokens.json`, `report.md` | **Supabase Postgres** |
| 블롭 | visual PNG, `*.scene`, export png/mp4 | **Supabase Storage 버킷** (public/signed URL = 기존 `/assets` 디스크 서빙 직접 대체) |

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
  grounds?, hash, created_at #   grounds = grounding 인용 추적(@vfs.md 메타 스키마)
```
- **sidecar `*.meta.json` → `meta jsonb` 컬럼으로 흡수**: 별도 파일 불필요, 논리경로엔 여전히 `*.meta.json`로 노출 가능. @vfs.md 메타 스키마 그대로.
- **`manifest.json` → `runs` 테이블 row**: History 전체 목록·상태 필터·재개가 쿼리로 즉시(파일 스캔 불요).

### 무료 근거 + 대안
- Supabase free: Postgres 500MB + Storage 1GB. 비활성 1주 일시정지 caveat → 핑/keep-alive로 회피(데모 허용 범위).
- 대안(추상화라 스왑 가능): **Turso(libSQL)** = 현 SqliteSaver 연속성 + **R2** 무료 블롭(2벤더) / **Neon** PG(블롭 별도).

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
| 갈림길 자동 판단(조건부 라우팅·게이트) | **`step_status` 값 + confirm/approve 엔드포인트.** critical→`BLOCKED` 기록 → 프론트가 다음 탭 잠금(@navigate.md③ · @review_subharness.md 게이트) |
| 세이브·이어하기(checkpointer interrupt/resume) | **상태가 이미 Supabase(manifest+VFS)에 영속.** 이어하기=manifest 읽고 그 지점부터 속행. 멈춤(interrupt)=하네스 루프가 AskUser 토스트에서 대기(WS), 응답 오면 루프 속행 |

### 왜 안 써도 되나 (근거)

1. **상태가 이미 영속** — §1에서 Supabase가 상태의 주인이 됨 → LangGraph의 존재 이유(checkpoint/resume)가 Supabase로 흡수. checkpointer를 또 두면 **두 상태원천**이 됨.
2. **이중 상태 동기화 고통 소멸** — 현 `server.py`는 `RUNS`(메모리)와 checkpointer를 수동 동기화하느라 주석이 도배돼 있고, 이 동기화 실수로 imaging 429 폭주 회귀까지 있었음(`server.py:162-165`). 단일 상태원천이면 이 버그 클래스가 통째로 사라짐.
3. **하네스는 DAG가 아니라 에이전트 루프** — 멀티턴·AskUser 토스트·도구 호출(@brainstorm_subharness.md①② · @design_subharness.md③)은 순서도 노드가 아니라 클로드 코드식 루프. 그래프 노드에 끼우면 어색.
4. **진행이 수동** — @navigate.md 모델 C에서 스튜디오 이동은 사용자 클릭. 자동 라우팅 엔진 불요.

### 대체 오케스트레이션 (구조)

- **스튜디오 내부** = 하네스 **에이전트 루프**: 시스템프롬프트+제약을 씌운 Claude/Gemini 호출 ↔ `VfsStore` CRUD(도구) ↔ AskUser 토스트(WS) 반복 → 산출물 VFS 영속.
- **스튜디오 사이** = API 엔드포인트 + `runs.step_status`: 스튜디오 종료 시 산출물 + `step_status` 갱신, 다음 스튜디오는 사용자가 트리거(@navigate.md).
- **게이트·재개** = `step_status` 값 + confirm/approve: 기존 `server.py` 엔드포인트 패턴은 유지하되 checkpointer 대신 **Supabase 읽기/쓰기**.
- 03 노드 로직(`brainstorm`/`generate`/`review`/`i18n_equiv`)은 **평범한 함수로 재사용** — 버리는 건 `graph.py`의 그래프 배선뿐.

---

## 3. Marker API (Q2 결정)

`front → API → (vfs | AI)`. API = 백엔드 게이트웨이(`server.py` FastAPI 확장). "Marker"의 실체 = 이 게이트웨이(하네스 조립 + VFS 영속) 자체.

### 3-1. 내부 VFS CRUD — 공유 스킬의 실체
- `VfsStore` **인프로세스 파이썬 인터페이스** = @brainstorm_subharness.md④ · @design_subharness.md③ · @review_subharness.md④ 가 공유하는 "파일시스템 CRUD 스킬"의 **실체**. (하네스는 자기 서버를 HTTP로 호출하지 않음.)
- 표면(논리경로 `/{runId}/{studio}/...`):

| 연산 | 의미 |
|---|---|
| `put(path, content, *, meta=None)` | 텍스트→Postgres row, 블롭→Storage 업로드+row. **미디어 put 시 `meta`(=sidecar) 자동 동시기록** |
| `get(path)` / `read_meta(path)` | 콘텐츠 / 메타 조회 |
| `list(prefix)` | 트리·History 열거 |
| `update(path, patch)` / `delete(path)` | 갱신 / 삭제 |
| `get_manifest(runId)` / `patch_manifest` / `set_step_status(runId, step, status)` | run 메타. **스텝 전환 → `runs` row 갱신(불변식)** |

- **불변식을 인터페이스가 강제**(@vfs.md CRUD 규약): ① 미디어 write → `meta` 동시기록, ② 스텝 전환 → manifest 갱신. 3 하네스가 일관성을 무상 획득.

### 3-2. AI 게이트웨이 — request 하네스 적용 / response 서빙
사용자 결정의 핵심. 모든 AI 프로바이더 호출이 이 경유를 거친다.

- **request 하네스 적용**: 스튜디오 AI 요청 도달 → 해당 하네스 6요소(시스템프롬프트·토큰제약·레퍼런스·구조화출력·크리틱·AskUser훅)를 **씌워 조립** → 프로바이더(Claude / GPT / Gemini / IMG.LY) 호출. **raw 프롬프트 직행 금지** = 현 조잡함(`prompt_builder.py` 단일샷) 원천 차단.
- **response 서빙**: 프로바이더 응답 → (a) `VfsStore.put`로 **VFS 영속**(+`meta.grounds` 기록) → (b) **프론트 서빙**(REST 응답 + 기존 WS `_publish` artifact/asset 이벤트 재사용, `server.py:139-159`).
- 원칙: **AI 산출물은 항상 VFS를 경유해 서빙** → grounding·메타·History가 자동으로 따라붙음.
- **엔타이틀먼트 게이트**(Refactor C4): Marker 하네스 · DeployStudio 어드바이저 호출은 **유료 티어($100/월)** 전용. 게이트웨이가 **단일 choke point**에서 entitlement 검사(무료 = raw Claude/GPT/Gemini만). 모델 선택은 Claude/GPT/Gemini 공통 지원(C2).

### 3-3. 프론트 표면 (얇게)
- 런 트리거: 기존 `/run` 등 유지.
- VFS read: `list`/`get` (History · 파일브라우저 · 에디터 로드).
- VFS save: 에디터 scene 편집 → `put` (IMG.LY 오버레이 저장, Refactor 51줄).
- asset 서빙: 기존 `GET /assets/{run_id}/{asset_id}.png` **일반화** → Storage public/signed URL 직링크 또는 `/vfs/{runId}/{path}`. WS는 기존 이벤트 재사용.

---

## 4. 기존 자산 재사용 / 변경점

- **재사용**: `server.py` run_id 스코프 · WS `_publish` · artifact/asset 이벤트 · `storage.py` env-스왑(monkeypatch 친화) 패턴 · 노드 로직(`brainstorm`/`generate`/`review`/`i18n_equiv`) 함수.
- **변경**: 로컬 PNG write → `VfsStore.put`(블롭) / `RUNS`·`:memory:` 휘발 → Supabase 영속 / 죽은 `DATABASE_URL` → 실 PG URL / **`graph.py` 그래프 배선 제거**(LangGraph 미사용, §2).

---

## 미결 / 후속 결정 항목

- 03 `graph.py` 그래프 배선 제거 + 노드 로직을 평범한 함수로 재사용 — 오케스트레이션 재작성 범위(§2).
- Supabase free **일시정지 대응**(핑/keep-alive 주기).
- 블롭 서빙: Storage **public 버킷 vs signed URL**(접근제어).
- `VfsStore` 논리경로 ↔ (`runs`/`vfs_nodes`) **매핑 규격 상세** + revise **버전닝/이력**(@vfs.md 미결과 연결).
- **오프라인/테스트 impl(로컬·인메모리) ↔ 라이브 impl(Supabase) 동등성 계약**(68 테스트 보존).
