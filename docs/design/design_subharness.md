# DesignStudio 서브 하네스 설계 (Marker Design Sub-harness)

> 대상: @Refactor.md §"백에서 반드시 정의되어야 하는 기획"(66~70줄) 중 DesignStudio 관련 4항목.
> 범위: 구조 결정만. 코드 구현·플랜 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 문서 (01·02 비참조)

---

## 0. 전제

- **입출력 계약**
  - 입력: BrainStormingStudio 산출물 — `spec.md` + `plan.md`(+ 가상 폴더의 리서치 asset).
  - 출력: **IMG.LY CE.SDK 구조화 씬**(A안). 평면 PNG 한 장이 아니라, 배경·텍스트·로고·CTA가 분리된 편집 가능한 레이어 씬.
  - 선택 근거: @Refactor.md 29줄(수동+에이전트 편집), 49줄(다국어 버전 각각 저장), 51줄(파일 클릭 시 에디터 오버레이) 요구를 동시에 만족하는 유일한 형태.

- **현재 코드의 조잡함 원인(이 설계가 해소하는 것)**
  - `prompt_builder.py:58-99` — 피사체·구도·팔레트·텍스트를 자연어 한 덩어리로 묶어 Imagen에 단일샷.
  - `prompt_builder.py:80-81` — 한국어 텍스트를 이미지 픽셀에 구움(글자 깨짐).
  - `gemini_client.py:11-14` — Imagen 한국어 약함 자인, 텍스트는 "CSS layer 별도 합성" 의도이나 미완.
  - `generate.py:337-363` — rough/comp/final이 LLM 재호출 없이 정적 번들 부착 = 이름뿐인 단계.
  - 레퍼런스(few-shot)·크리틱 패스 전무 → 결과가 평균값(AI 슬롭)으로 수렴.

---

## ① 모델 교차 이용 / 역할 분담 (Refactor 69줄)

A안 = 비주얼·텍스트·레이아웃 **분리**. 3-액터 구조.

| 액터 | 역할 | 책임 경계 |
|---|---|---|
| **Marker** (Claude 기반 디자인 하네스) | 아트디렉터·디자이너 | 레이아웃 스펙(JSON)·카피·컴포넌트 배치·디자인 비평(크리틱) |
| **Gemini** (Imagen / Nano Banana) | 비주얼 소재 생성기 | **텍스트 없는** 배경·키비주얼·제품컷만 (텍스트 책임 제거) |
| **IMG.LY CE.SDK** | 렌더·편집 기질 | Marker 스펙 → scene 조립, 레이어 편집·다국어 텍스트 교체·가상폴더 저장 |

원칙: **텍스트와 레이아웃은 절대 Gemini가 픽셀로 렌더하지 않는다.** 텍스트는 IMG.LY 텍스트 레이어로만 존재한다(다국어 교체·검수·수정의 전제).

---

## ② 디자인 서브 파이프라인 (Refactor 52줄 구체화)

```
S0 셋업     plan.md 파싱 → 디자인 토큰 lock(palette·font·grid·aspect)
            + 소재 매트릭스(채널 × 언어) 산출

S1 Rough    Marker가 레이아웃 스켈레톤 결정:
 (방향)       그리드 + 컴포넌트 슬롯(배경/헤드라인/서브/로고/CTA/고지) + 비주얼 컨셉 + 카피 초안
            → [confirm 게이트]

S2 컴포넌트   2a 비주얼 : Gemini가 배경/키비주얼 생성 (텍스트 free)
   빌드       2b 카피·타이포 : Marker가 헤드라인/바디/CTA 확정 + 타입스케일
                              + grounding 검증(금융 수치 환각 차단, generate.py 로직 재사용)
            2c 브랜드·컴플 : 로고 · AI생성 고지 · 필수 디스클로저 배치
            → [confirm 게이트 — 컴포넌트별 승인/재생성]

S3 Final    IMG.LY scene 합성 → Marker 크리틱 패스(디자인 루브릭 채점 → 재생성 제안)
 (검수)      → [confirm 게이트 — final 확정]

다국어      비주얼·레이아웃 공유, 2b 텍스트 레이어만 언어별 생성 → 언어별 scene 저장 (Refactor 49줄)

산출        확정 scene(언어별) + ReviewStudio용 메타데이터(최종 텍스트 + 콘티, Refactor 54줄)
```

- `generate.py`의 rough/comp/final(현재 정적 번들)을 위 **실제 단계**로 승격한다.
- grounding 검증(`generate.py`의 `_grounding_check`)은 S2b에서 재사용 — 상품 마스터에 없는 금리·만기 토큰 차단.

### confirm 정책 (단계 게이트 + bypass)

- **기본값**: S1 / S2(2a·2b·2c) / S3 **각 단계마다 confirm 게이트 ON**.
- **bypass**: DesignStudio **Setting**(Refactor 27줄 사이드바)에서 게이트를 끌 수 있다.
  - 게이트 **단위 토글**(예: Rough만 확인, 나머지 자동) 지원.
  - bypass ON 시 사람 승인 대신 **Marker 크리틱 패스가 품질 게이트**로 동작(자동 재생성), 산출 완료는 알림으로 통지.
- **AskUser 훅과의 관계**: confirm 게이트 = 단계 산출물 승인. AskUser 훅(Refactor 44줄, 웹소켓 선택 UI) = 중간 분기 의사결정. bypass 시 AskUser 분기는 Marker가 기본값으로 자동 결정.

---

## ③ Marker 디자인 하네스 정의 (Refactor 67줄 — 조잡함 해결 핵심)

하네스 = 클로드 API 호출을 감싸는 6 구성요소 + 공유 파일시스템 CRUD 스킬.

| 구성요소 | 내용 | 비고 |
|---|---|---|
| **시스템 프롬프트** | 금융 마케팅 디자인 원칙(위계·그리드·여백·CTA 배치·컴플라이언스 톤) | 도메인 전문성 인코딩 |
| **디자인 토큰(제약)** | `brief.creative_direction`을 lock(palette·font·grid·aspect) | 매 호출 랜덤화 방지 |
| **레퍼런스(few-shot)** | 프로 마케팅물 예시 주입 | **현재 전무 → 품질 점프 최대 레버** |
| **구조화 출력** | 레이아웃 스펙 JSON (픽셀 아님) | IMG.LY scene 조립용 |
| **크리틱 패스** | 시니어 아트디렉터 루브릭 채점 → 재생성 | bypass 시 자동 품질 게이트 |
| **AskUser 훅** | 웹소켓 선택 UI(Refactor 44줄 패턴 재사용) | 디자인 분기 결정용 |
| **파일시스템 CRUD 스킬** | 가상 폴더 트리 read/write/update/delete (visuals·scenes·exports·meta 저장/갱신, 사용자 추가 asset 읽기) | BrainStorming Marker 하네스와 **공유 스킬**(@brainstorm_subharness.md ④). 실체 = @marker_api.md §3-1 `VfsStore` |

- "Marker" 모델 = 위 하네스가 씌워진 Claude. 모델 선택 UI 최상단 노출(Refactor 39줄). 일반 Claude/GPT/Gemini와 구분되는 것은 **이 6요소의 조립**.
- BrainStorming의 Marker 하네스(기획)와 동일 패턴, 도메인만 "디자인"으로 교체.

---

## ④ 가상 폴더 산출물 구조 (Refactor 70줄 — CRUD 대상)

> 폴더 트리 SSOT = @vfs.md. 아래는 `/design/` 발췌.

```
/{runId}/design/
  rough/                 # S1: layout.spec.json + 와이어
  design-system/         # S2: 토큰 + 컴포넌트 카탈로그 (History 시각화)
    tokens.json          #   palette·font·grid·aspect
    components/{visual, headline, body, cta, logo, disclosure}/
  final/{ko,vi,en}/      # S3: *.scene + export(png/mp4)
  metadata.md            # ReviewStudio용 텍스트+콘티 메타
```

- 언어별 `final/{lang}`은 `design-system/`을 공유하고 텍스트 컴포넌트만 분기.
- `metadata.md`는 DesignStudio 최종 확정 시 기록 → ReviewStudio가 비전 AI 검수 없이도 1차 판단(Refactor 54·58줄).
- 모든 미디어 asset은 sidecar `*.meta.json` 동반(@vfs.md 메타 스키마).

---

## 미결 / 후속 결정 항목

- 디자인 토큰·레퍼런스 라이브러리의 **출처와 큐레이션 방식**(few-shot 예시를 어디서 확보·관리할지).
- 크리틱 패스 **루브릭의 구체 항목**(채점 기준).
- IMG.LY scene **스키마와 Marker 레이아웃 스펙 JSON의 매핑** 규격.
- 가상 폴더 트리 **CRUD API 표면** — BrainStorming Marker 하네스와 공유 확정(@brainstorm_subharness.md ④와 동일 스킬), 인터페이스 = @marker_api.md §3-1 `VfsStore`에서 확정.
- **ReviewStudio iteration 수신** — `review/revise/` 권장을 DesignStudio가 받아 수정하는 경로(수정 모드/자동수정 귀속). @review_subharness.md③ 미결과 연결.
