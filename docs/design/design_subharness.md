# DesignStudio 서브 하네스 설계 (Marker Design Sub-harness)

> 대상: @Refactor.md §"백에서 반드시 정의되어야 하는 기획"(66~70줄) 중 DesignStudio 관련 4항목.
> 범위: 구조 결정만. 코드 구현·플랜 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app·frontend)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화 · 2026-06-12 — T3 반영(design/ 패키지·pipeline.py 좌표, pending_ask 해소, §⑤ 영상 장착 지점). 점검 보고서 @harness_audit.md

---

## 0. 전제

- **입출력 계약**
  - 입력: BrainStormingStudio 산출물 — `spec.md` + `plan.md`(+ 가상 폴더의 리서치 asset).
  - 출력: **구조화 씬(A안)**. 평면 PNG 한 장이 아니라, 배경·텍스트·로고·CTA가 분리된 편집 가능한 레이어 씬.
  - A안의 구현은 **Fabric.js** — `FabricScene {version:"6.0.0", objects, width, height}`(frontend/lib/sceneAssembler.ts:16-19), 에디터=DesignEditor.tsx+useFabricCanvas.ts, 언어 교체=`swapLanguage`(sceneAssembler.ts:75-90). IMG.LY/CE.SDK 코드는 프론트에 부재(상용 라이선스 기각 이력 — 분리 레이어 씬이라는 결정 자체는 보존).
  - 선택 근거: @Refactor.md 29줄(수동+에이전트 편집), 49줄(다국어 버전 각각 저장), 51줄(파일 클릭 시 에디터 오버레이) 요구를 동시에 만족하는 유일한 형태.

- **설계 당시(mvp/03) 코드의 조잡함 원인 — 역사 기록(아래 파일들은 현 레포에 부재, 이 설계가 해소한 것)**
  - `prompt_builder.py:58-99` — 피사체·구도·팔레트·텍스트를 자연어 한 덩어리로 묶어 Imagen에 단일샷.
  - `prompt_builder.py:80-81` — 한국어 텍스트를 이미지 픽셀에 구움(글자 깨짐).
  - `gemini_client.py:11-14` — Imagen 한국어 약함 자인, 텍스트는 "CSS layer 별도 합성" 의도이나 미완.
  - `generate.py:337-363` — rough/comp/final이 LLM 재호출 없이 정적 번들 부착 = 이름뿐인 단계.
  - 레퍼런스(few-shot)·크리틱 패스 전무 → 결과가 평균값(AI 슬롭)으로 수렴.
  - → **현 구현 상태**: grounding은 core/grounding.py(`build_corpus`·`find_ungrounded`)로 구현되어 S2b 생성(backend/app/gateway/design/steps.py S2bCopy.run:218-256)·critic 게이트(S2bCopy.critic_gate:258-269) 양쪽에서 사용. 단계 승격=단계 선언 유도 STEPS(design/steps.py:379-382)+PipelineOrchestrator(gateway/pipeline.py) 상태머신으로 구현 완료. 레퍼런스 주입·크리틱 패스도 구현(§③).

---

## ① 모델 교차 이용 / 역할 분담 (Refactor 69줄)

A안 = 비주얼·텍스트·레이아웃 **분리**. 3-액터 구조.

| 액터 | 역할 | 책임 경계 |
|---|---|---|
| **Marker** (Claude 기반 디자인 하네스) | 아트디렉터·디자이너 | 레이아웃 스펙(JSON)·카피·컴포넌트 배치·디자인 비평(크리틱) |
| **Gemini** (Imagen / Nano Banana) | 비주얼 소재 생성기 | **텍스트 없는** 배경·키비주얼·제품컷만 (텍스트 책임 제거) |
| **Fabric.js** (프론트 렌더·편집 기질) | 렌더·편집 기질 | Marker layout.spec → FabricScene 조립(frontend/lib/sceneAssembler.ts), 캔버스 레이어 편집(DesignEditor.tsx+useFabricCanvas.ts)·다국어 텍스트 교체(`swapLanguage`)·가상폴더 저장(design/final/{lang}/main.scene). 당초 IMG.LY CE.SDK 채택이었으나 상용 라이선스로 기각(결정 이력 보존) |

원칙: **텍스트와 레이아웃은 절대 Gemini가 픽셀로 렌더하지 않는다.** 텍스트는 Fabric textbox 레이어로만 존재한다(다국어 교체·검수·수정의 전제).

---

## ② 디자인 서브 파이프라인 (Refactor 52줄 구체화)

```
S0 셋업     plan.md 파싱 → 디자인 토큰 lock(palette·font·grid·aspect)
            — 서술형 creative_direction(concept/visual_mood/color_palette/typography) 보존
            + aspect 미기재 시 material_matrix 추론 폴백 + languages 정규화(design/steps.py S0Setup.run:103-138)
            + 소재 매트릭스(채널 × 언어) 산출

S1 Rough    Marker가 레이아웃 스켈레톤 결정:
 (방향)       그리드 + 컴포넌트 슬롯(배경/헤드라인/서브/로고/CTA/고지) + 비주얼 컨셉 + 카피 초안
            → [confirm 게이트]

S2 컴포넌트   2a 비주얼 : Gemini가 배경/키비주얼 생성 (텍스트 free)
   빌드                   — 이미지 생성 실패 시 placeholder 그라데이션 폴백(design/steps.py S2aVisual.run:194-200)
            2b 카피·타이포 : Marker가 헤드라인/바디/CTA 확정 + 타입스케일
                              + grounding 검증(금융 수치 환각 차단, core/grounding.py)
            2c 브랜드·컴플 : 로고 · AI생성 고지 · 필수 디스클로저 배치
            → [confirm 게이트 — 컴포넌트별 승인/재생성]

S3 Final    백엔드 S3Final은 metadata.md만 생성(scene 합성 없음, 아래 상세)
 (검수)      + Marker 크리틱 패스(디자인 루브릭 채점)
            → [confirm 게이트 — final 확정]

다국어      비주얼·레이아웃 공유, 2b 텍스트 레이어만 언어별 생성 → 프론트가 언어별 scene 저장 (Refactor 49줄)

산출        layout.spec.json(전 언어 copy 병합) + metadata.md(ReviewStudio용 최종 텍스트+콘티, Refactor 54줄)
            — final scene(언어별)은 프론트가 조립·저장(아래 상세)
```

- **final scene 조립 주체(spec §9-3)**: 백엔드 S3(`S3Final.run`, backend/app/gateway/design/steps.py:328-371)는 **metadata.md만 생성 — scene을 합성하지 않는다**. final scene 조립=**프론트 `CockpitProvider.assembleScenes`**(frontend/components/cockpit/CockpitProvider.tsx:340-368, design done 시 일괄 :473-485)가 layout.spec.json을 읽어 전 언어 수행, `design/final/{lang}/main.scene`으로 PUT /vfs 저장(scene-wins: 수동 편집한 언어는 스킵). **cross-actor 계약**: ReviewHarness `_collect_scene_copy`(harness_review.py:218-249)가 main.scene `{version, objects}`의 textbox에서 role→text로 카피를 복원, 없으면 layout.spec.json[copy][lang] 폴백. scene 조립 로직은 frontend/lib/sceneAssembler.ts:49-73.
- grounding 검증은 core/grounding.py(`build_corpus`·`find_ungrounded`)로 구현 — S2b 생성(design/steps.py:218-256)·critic 게이트(:258-269) 양쪽 사용, factsheet에 없는 금리·만기 토큰 차단. (설계 당시 "generate.py 로직 재사용" 인용은 mvp/03 배경 — 역사 기록.)
- 단계 승격: 설계 당시 mvp/03 `generate.py`의 rough/comp/final(정적 번들)을 실제 단계로 승격한다는 목표는 STEPS(단계 선언 유도, design/steps.py:379-382)+PipelineOrchestrator(gateway/pipeline.py)로 구현 완료.

### confirm 정책 (단계 게이트 + bypass)

- **(1) 게이트 정지** = `GateEnvelope(kind="confirm", step, critic, auto_advanced, actions=["confirm","regenerate"])`(gateway/pipeline.py _gate_result:182-198). 승인 action=`advance|confirm`(pipeline.py CONFIRM_ACTIONS :55·승인 분기 :109-112). 게이트 대상=GATED_STEPS(S1·S2a·S2b·S2c·S3 — design/steps.py:381), S0은 비게이트.
- **(2) bypass**: DesignStudio **Setting**(Refactor 27줄 사이드바)에서 게이트 **단위 토글**(예: Rough만 확인, 나머지 자동). bypass 시 critic 품질게이트는 **S1·S3(7항목 시각 critic)·S2b(grounding ungrounded 수치)만 — S2a/S2c는 critic 없음(항상 통과)**(GATED_STEPS·CRITIC_STEPS design/steps.py:381-382, 단계별 critic_gate — S1:172-175·S2b:258-269·S3:373-375, S2a/S2c는 기본 pass).
- **(3) 자동 재생성**: bypass에서 critic 실패 시 step당 1회 한도로 재생성, 2차 실패 시 meta.warnings 기록 후 진행(gateway/pipeline.py:152-161).
- **(4) done**: gate 없음 + meta.auto_advanced(자동 통과 단계 목록, gateway/pipeline.py:135-145).
- **AskUser 훅과의 관계**: design은 ask 게이트 없음(design의 게이트는 kind=confirm만) — ask는 brainstorming 전용. design state의 `pending_ask` 잔재 키는 T3 P2가 제거(default 제외+로드 시 pop, harness_design.py:76 — @harness_audit.md §2-7).
- wire 상세(WS/HTTP 봉투)는 @ws_protocol.md.

---

## ③ Marker 디자인 하네스 정의 (Refactor 67줄 — 조잡함 해결 핵심)

하네스 = 클로드 API 호출을 감싸는 6 구성요소 + 공유 파일시스템 CRUD 스킬.

| 구성요소 | 내용 | 비고 |
|---|---|---|
| **시스템 프롬프트** | 금융 마케팅 디자인 원칙(위계·그리드·여백·CTA 배치·컴플라이언스 톤) | 도메인 전문성 인코딩 |
| **디자인 토큰(제약)** | `brief.creative_direction`을 lock(palette·font·grid·aspect) | 매 호출 랜덤화 방지 |
| **레퍼런스(few-shot)** | 프로 마케팅물 예시 주입 | **구현됨** — `load_references`(backend/app/references/design/*.json, design/steps.py:80-88)가 S1Rough.run 프롬프트 references 블록에 주입(:150-157) |
| **구조화 출력** | 레이아웃 스펙 JSON (픽셀 아님) | Fabric scene 조립용(프론트 sceneAssembler.ts) |
| **크리틱 패스** | 시니어 아트디렉터 루브릭 채점 → 재생성 | bypass 시 자동 품질 게이트 |
| **AskUser 훅** | design은 ask 게이트 없음(게이트는 kind=confirm만) — ask는 brainstorming 전용(설계 당시 의도는 디자인 분기용 웹소켓 선택 UI — 구현에서 미채택) | state의 `pending_ask` 잔재 키는 T3 P2가 제거(로드 시 pop — @harness_audit.md §2-7) |
| **파일시스템 CRUD 스킬** | 가상 폴더 트리 read/write/update/delete (visuals·scenes·exports·meta 저장/갱신, 사용자 추가 asset 읽기) | BrainStorming Marker 하네스와 **공유 스킬**(@brainstorm_subharness.md ④). 실체 = @marker_api.md §3-1 `VfsStore` |

- **실체 매핑**: 프롬프트 4요소(시스템 프롬프트·디자인 토큰·레퍼런스·구조화 출력)=`PromptSpec`(gateway/prompt.py) 조립, 크리틱 패스=`CriticVerdict`(gateway/critic.py) 표준 봉투, AskUser/confirm 게이트=`GateEnvelope`(gateway/harness.py).

- "Marker" 모델 = 위 하네스가 씌워진 Claude. 모델 선택 UI 최상단 노출(Refactor 39줄). 일반 Claude/GPT/Gemini와 구분되는 것은 **이 6요소의 조립**.
- BrainStorming의 Marker 하네스(기획)와 동일 패턴, 도메인만 "디자인"으로 교체.

---

## ④ 가상 폴더 산출물 구조 (Refactor 70줄 — CRUD 대상)

> 폴더 트리 SSOT = @vfs.md. 아래는 `/design/` 발췌.

```
/{runId}/design/
  _state.json            # 하네스 상태 단일주인(step·gate·confirmed·bypass·languages)(pending_ask 잔재는 T3 P2 제거 — 로드 시 pop)
  _material_matrix.json  # S0: 소재 매트릭스(design/steps.py:128-130)
  rough/                 # S1: layout.spec.json — 단일 소스(S2b 카피·S2c 고지가 [copy][lang]에 병합 design/steps.py:243-252·:307-314)
  design-system/         # S0·S2: 토큰 + 컴포넌트 카탈로그 (History 시각화)
    tokens.json          #   palette·font·grid·aspect(+서술형 creative_direction 보존)
    components/{visual, headline, body, cta, logo, disclosure}/
  final/{ko,vi,en}/      # main.scene — 프론트(assembleScenes)가 기록. export(png/mp4)는 미구현
  metadata.md            # S3: ReviewStudio용 텍스트+콘티+크리틱+시각적법성 메타
```

- 언어별 `final/{lang}`은 `design-system/`을 공유하고 텍스트 컴포넌트만 분기.
- `final/{lang}/main.scene`은 프론트가 기록(§② final scene 조립 주체). export(png/mp4)는 미구현 — 합성 렌더는 프론트가 `review/_render/{lang}.png`로 업로드(frontend/lib/sceneRender.ts:66).
- `metadata.md`는 DesignStudio 최종 확정 시 기록 → ReviewStudio가 비전 AI 검수 없이도 1차 판단(Refactor 54·58줄).
- 미디어 asset의 메타는 sidecar 파일이 아니라 **노드 내장 meta**(`VfsStore.read_meta`)로 저장(@vfs.md 메타 스키마).

---

## ⑤ 영상 파이프라인 장착 지점 (예약 — 문서만, T3 spec §6)

> 코드 없음. 새 매체(영상 등) 파이프라인 추가에 필요한 것이 무엇인지(=3가지뿐)를 고정해,
> 골격 재설계 없이 장착 가능함을 기록한다. **단계 이름·개수는 그 매체의 기획 산출물이므로
> 여기 적지 않는다**(기획 선점 방지 — 장착 메커니즘만 기술).

새 매체 파이프라인 추가에 필요한 3가지(`gateway/pipeline.py` 골격이 나머지를 제공):

1. **단계 목록 정의** — `PipelineStep` 구현 클래스 시퀀스. 매체 프로바이더는 단계 생성자
   주입(`S2aVisual(image_provider)` 전례 — design/steps.py:184-185). critic이 필요한
   단계만 `critic_gate` 오버라이드(기본 = 항상 통과).
2. **같은 `PipelineOrchestrator`에 장착** — 게이트 4분기·bypass 연쇄·critic·1회 자동
   재생성·warnings·auto_advanced는 골격이 제공하므로 제어 루프 복제 불필요. 골격의
   design 비의존성은 가짜 단계 단위 테스트(backend/tests/test_pipeline.py)가 보증.
3. **done 처리·state 주입** — done_text·done_output(산출 경로)·studio(step_status 어휘)·
   save_state 규약·`_load_state` default 제공(DesignHarness 전례 — harness_design.py:53-79).

- 골격 밖 배선 2곳(3요소에 비포함 — 장착 시 함께): ⑴ `gateway/registry.py` `select_harness`의
  studio 분기·`media_provider_factory` 배선(새 하네스 노출 지점, :16-22) ⑵ `providers/base.py`
  `Provider`에 매체 메서드 확장(현행은 `generate_image`뿐, :41 — fake/demo 구현 동반).
- 산출물 수신 경로는 @vfs.md `review/revise/{image,text,video}` 예약과 연결 — ReviewStudio
  R3 수정 지시가 매체별로 귀속되는 자리(iteration 수신 경로 자체는 미결 — 아래 미결 항목 참조).

---

## 미결 / 후속 결정 항목 (disposition: 2026-06-11)

- 디자인 토큰·레퍼런스 라이브러리의 **출처와 큐레이션 방식** → **채택**: backend/app/references/design/*.json — `load_references`(design/steps.py:80-88)가 S1Rough.run 프롬프트 references 블록에 주입(:150-157).
- 크리틱 패스 **루브릭의 구체 항목** → **확정**: 단계별 critic_gate(design/steps.py — S1:172-175·S2b:258-269·S3:373-375, S2a/S2c는 기본 pass) — S1·S3=7항목 시각 critic(hierarchy/grid/whitespace/cta/compliance/copy_visual/brand), S2b=grounding ungrounded 수치, S2a/S2c=critic 없음.
- scene **스키마와 Marker 레이아웃 스펙 JSON의 매핑** 규격 → **확정(Fabric)**: `assembleScene`(sceneAssembler.ts:49-73) + `swapLanguage`(:75-90).
- 가상 폴더 트리 **CRUD API 표면** → **확정**: `VfsStore` ABC — BrainStorming Marker 하네스와 공유(@brainstorm_subharness.md ④와 동일 스킬), 인터페이스 = @marker_api.md §3-1.
- **ReviewStudio iteration 수신 — 미결 유지**: `review/revise/` 권장을 DesignStudio가 받아 수정하는 경로(수정 모드/자동수정 귀속). design `regenerate` 액션이 부분 대체하나 정식 경로는 후속 과제. @review_subharness.md③ 미결과 연결.
- **done 통지 UI(구상)**: 현재 done은 HTTP 응답 text·meta로만 표면화 — 별도 알림 UI는 미구현(후속 과제).
