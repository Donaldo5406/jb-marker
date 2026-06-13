# T1 하네스 점검 보고서 (harness audit) — 발견 18건 현황 · 의도적 보존 · 구 용어 매핑

> 작성: 2026-06-11 (T1-P5) · 근거 spec: @../specs/2026-06-10-harness-correction-openapi-design.md (§1 발견 · §4~§8 교정 설계)
> 관련: @ws_protocol.md (WS 단일 레퍼런스 — 같은 PR에서 생성)
> **인용 기준**: 교정 전 인용은 baseline `bd6c5a5`(T1 착수 직전 main) 기준, 현행 인용은 `48636b0`(P4 머지) 기준 — **spec §1의 줄번호(`harness.py:44-63` 등)는 baseline 기준이므로 현행 트리에서 무효**. 현행 좌표는 본 문서 §1 표의 '교정/보존 현황' 열을 보라.
> **T3 갱신(2026-06-12)**: T3 P2가 harness_design.py를 gateway/design/{prompts,scoring,steps}.py + gateway/pipeline.py(오케스트레이터)로 분해 — §1 표의 harness_design.py '현행' 인용은 48636b0 기준(분해 전)이므로 현행 좌표는 §3 매핑 표 하단의 T3 행으로 환산하라. T3 표기: §2-7 해소(백로그 ⑤) · §1-8 보강(백로그 ③ — T3 P3) · §2-1·6·9는 보존 유지에 T3 P2 좌표 이동만 반영. T3 표기 좌표는 P3 코드 최종 커밋 `b09b063` 기준.

독자: 이 레포의 과거 문서·코드(스펙·플랜·구 설계문서)를 읽는 개발자. T1 spec §1이 2026-06-10 코드 정밀 조사에서 발견한 18건에 대해 ①전수의 현황(교정 위치 grounding) ②의도적 보존 항목과 사유 ③구 용어→현행 매핑을 기록한다.

---

## 1. 발견사항 18건 현황

상태 어휘: **교정**(P1~P4에서 코드 교정 완료) · **P5에서 해소**(코드 선행 완료, 문서가 본 PR에서 갱신) · **의도 보존**(결정에 따라 유지).

| # | 발견(spec §1 요약) | 상태 | 교정/보존 현황(현행 파일:줄) | 교정 설계(spec §) |
| --- | --- | --- | --- | --- |
| 1 | **6요소 ABC 장식화** — 6요소(system_prompt·constraints·references·structured_output·critic·askuser_hook) 선언 대비 constraints/references/structured_output_schema/askuser_hook 호출처 전무, 실제 조립은 각 하네스 handle_turn 내부 인라인 f-string | 교정 | Harness ABC 최소 계약 harness.py:71-86(독스트링 :72-77이 제거를 명기) · 죽은 메서드 grep 0건 · 6요소는 PromptSpec(prompt.py:12-30 — assemble :20-26 · meta :28-30)으로 실체화 · 사용 4곳: harness_brainstorming.py:162·229·316 / harness_design.py:307·357·478 / harness_review.py:411·498 / deploy/advisor/chat.py:67 | §5.1 |
| 2 | **HITL 게이트 프로토콜 3종 분기** — brainstorming `HarnessResult.ask`(AskPayload) / design `meta["gate"]` / review step_status+acknowledged 플래그. 프론트가 스튜디오별 3벌 분기 유지, 스튜디오 추가 시 4벌째 | 교정 | GateEnvelope harness.py:29-59(to_dict :51-59) + HarnessResult.gate(:67) · brainstorming `_to_gate`(kind=ask, actions=["answer"]) harness_brainstorming.py:74-81 · design kind=confirm harness_design.py:240-242, done은 gate 미설정+meta.auto_advanced(:194-203) · review `_actions_for` harness_review.py:42-48 + kind=status(:594-597) · HTTP 4키 고정 routers/gateway.py:93-95 + GatewayRunOut(schemas.py:220-226) · 구 신호(AskPayload·meta["gate"]) 코드 0건(테스트 단언 잔존: tests/test_gate_envelope.py:112·136) · 프론트는 applyGate 단일 적용점(CockpitProvider.tsx:393-413) + kind별 상태 3분배(ask→pendingGate · confirm→designGate · status→reviewGate), AskUserToast.tsx:44는 `kind==="ask"`만 렌더 | §4 |
| 3 | **critic 시그니처 3종** — 베이스 `critic(draft:str)->str` / brainstorming `->list[str]` / design `(scores:dict)->dict` / review 미사용(compute_gate 대체). 베이스 계약 무의미 | 교정 | CriticVerdict critic.py:6-21(passed/issues/scores · to_dict · from_scores) · 베이스 critic 제거 · brainstorming critic/critic_spec→CriticVerdict(harness_brainstorming.py:101·111) · design 출구 봉투화(harness_design.py:256 from_scores · :267-268 S2b ungrounded→issues) · review는 종전대로 compute_gate(critic 미사용 — §6 '무변경') | §6+§5.1 |
| 4 | **엔타이틀먼트 단일 choke 위반** — gateway.run은 env_override OR check로 게이트하나 advisor chat·dispatch는 `entitlement.check(user_id)`만 직접 호출해 override 무시 → override=true에서 advisor/dispatch만 402 불일치 | 교정 | entitlement.py:28-36 `is_entitled`(= env override OR store, set_override_source :22-25 · server.py:79 주입) · 호출처 전원 단일화: server.py:93(gateway 배선) · routers/deploy.py:191(advisor chat) · :222(dispatch) · routers/meta.py:27·38(GET/PUT) · routers/deploy.py:311(_state dev_pass) · MarkerGateway env_override 인자 제거(gateway/gateway.py:19-26) | §7-1 |
| 5 | **이미지·비전 usage 미기록** — _TrackedProvider에 generate_image/review_image 추적 코드가 있으나 image_provider/vision_provider 주입이 비래핑 _ModelBoundProvider라 도달 불가(죽은 코드), 이미지·비전 비용 통째 누락 | 교정 | routers/gateway.py:70-73 `_media_provider`가 tracked_provider()로 래핑 후 select_harness 주입(gateway/registry.py:19·22) · providers/wrappers.py:58-74 generate_image/review_image가 record_usage, :62 모델명 하드코딩→settings.google_image_model | §7-2 |
| 6 | **DemoProvider 마커 스니핑** — 단계 감지가 system 프롬프트의 문자열 마커에 의존, 프롬프트 문구 수정만으로 mock 시연 파이프라인 파손 가능 | 교정 | providers/demo.py:262-296 — (meta[studio], meta[step]) 8키 라우팅(stage_a/stage_b/S1/S2b/critic/R1/R2/R3), meta 부재 시 빈 reply(:293-296) · 콘텐츠 검사(legal_findings :39-85)는 불변 · 래퍼 meta 패스스루 wrappers.py:24-25·49-50 | §5.2 |
| 7 | **중복 코드** — `_parse_json` 3벌(brainstorming/design/legal_search) · `_frontmatter` 2벌 · `_Empty` 더미 2벌 · normalize_languages 방어 패턴 4곳 | 교정 | core/parsing.py:16-50(parse_json_block · parse_frontmatter · read_json_node) · 소비처 import 단일화(harness_brainstorming.py:15 · harness_design.py:20 · harness_review.py:17 · core/legal_search.py:43) · normalize_languages = core/lang.py:57 1벌 | §7-3 |
| 8 | **`model=req.provider` 암묵 계약** — 하네스가 provider "이름"을 model 인자로 전달, _ModelBoundProvider는 이를 버리고 자체 바인딩 사용. 실 Provider 직접 주입 시 잘못된 모델명 호출 함정 | 교정 | `model=req.provider` grep 0건 · 모델 결정 단일 책임 = ModelBoundProvider(wrappers.py:22-25 — model 인자 무시 · self._model 강제) · 잔여 동류였던 brainstorming `_summarize`/`_window_for_provider`의 죽은 model 파라미터(req.provider 전달)는 T3 P3(백로그 ③)에서 제거 | §5.3 |
| 9 | **`meta.grounds` 미영속** — marker_api.md §3-2 "VFS 영속(+meta.grounds 기록)" 약속 대비 기록처는 Passthrough 빈 리스트뿐. S2b ungrounded·리서치 citation이 노드 meta에 부재 → 감사추적 미달성 | 교정 | brainstorming spec.md put 시 grounds=citation URL들(harness_brainstorming.py:249-251) · design S2b layout.spec.json에 `{corpus:"factsheet", ungrounded:[...]}`(harness_design.py:381-385) · Passthrough `[]`(harness.py:101) · 책임 선언 gateway/gateway.py:5 | §7-5 |
| 10 | **AdvisorHarness 계약 이탈** — deploy_studio.md "하네스 아님" 선언과 달리 파일·클래스명이 하네스(gateway/harness_advisor.py). Harness ABC 미상속·provider 계약 상이(.chat)·vfs.get_text/put_text는 ABC에 없는 구현체 전용 메서드 암묵 의존 | 교정 | deploy/advisor/chat.py:18 DeployAdvisor(독스트링 :1-5 "하네스가 아니다") · gateway/harness_advisor.py 삭제 · get_text/put_text ABC 승격 vfs/base.py:47-55("T1-P1" 주석) · JSONL race는 의도 보존(§2-3 참조) | §7-6 |
| 11 | **WS 이벤트 키 불일치** — artifact/askuser는 `type` 키, restored만 `kind` 키. 프론트 RunEvent는 `type`만 알아 restored WS 이벤트는 버려짐 | 교정 | routers/gateway.py:88-90 `{type:"session", event:"restored", studio, run_id}` · 프론트 RunEvent 반영 useRunSocket.ts:8 · 회귀 가드 tests/test_server_response_hygiene.py:38 · ⚠️ session/store.py:94의 `{kind:"restored"}`는 WS가 아닌 HTTP resume 응답 본문(SessionRestoredOut, schemas.py:132-136) — 별개 계약이므로 혼동 주의 | §7-7 |
| 12 | **설계문서 괴리 4건** — brainstorm_subharness.md(bypass 정책: 코드는 제거됨) · marker_api.md(영속 책임: 게이트웨이→하네스 이동) · design_subharness.md(final scene 조립: 백엔드 기재 vs 실제 프론트) · deploy_studio.md(advisor 명명) | P5에서 해소 | 코드측 선행 교정 완료: bypass 제거 harness_brainstorming.py:259 · 영속=하네스 책임 gateway/gateway.py:5 · final scene=프론트 CockpitProvider.tsx assembleScenes(:340-368) · advisor 개명 chat.py:18 — 문서 갱신은 본 PR(P5)의 marker_api · subharness 3건 · deploy_studio · vfs.md | §9-3 |
| 13 | **응답 스키마 전무** — 23개 HTTP 엔드포인트 전부 `-> dict` raw 반환, response_model·tags·summary 0건. 요청만 Pydantic 8종인 비대칭 | 교정 | schemas.py 모델 29종(가변 키=dict 유지 원칙 :1-9 docstring) · routers/ 8파일 response_model 22건 + preview HTMLResponse(history.py:25) · 전 라우트 summary · openapi_tags 8종 + version 0.4.0(server.py:26-41) · 계약 테스트 tests/test_openapi_contract.py | §8.2 |
| 14 | **securityScheme 미모델링** — 인증이 커스텀 의존성이라 OpenAPI 보안 스킴 부재·Swagger Authorize 불가, 401/402/404/400/422 에러 계약 미문서화 | 교정 | routers/deps.py:22 HTTPBearer(auto_error=False) · :25-31 get_user_id(표기 전용 _cred + 실검증 auth.resolve_user_id, 행동 3종 보존 :6-10) · AUTH_RESPONSES/OWNER_RESPONSES(schemas.py:25-26) | §8.2 |
| 15 | **다형 응답 미표현** — `GET /vfs/{run_id}/{rest}`는 블롭=바이너리/텍스트=JSON, `GET /runs/{id}/preview`는 text/html — OpenAPI responses 분기 부재 | 교정 | routers/vfs.py:38-42 responses 200 분기(JSON \| octet-stream \| image/png), 구현 :49-51 · history.py:25-27 HTMLResponse | §8.2 |
| 16 | **advisor 응답 내부 키 누출** — `_usage`/`_model`이 HTTP 응답에 그대로 노출 | 교정 | routers/deploy.py:199-209 — record_usage 영속 후 _usage/_model pop(:208-209) · DeployAdvisor 내부 echo는 유지(chat.py:78-80 — 호출자용), HTTP 표면에서만 제거 | §8.2 |
| 17 | **WS 프로토콜 통합 문서 부재** — 이벤트 정의가 M3 spec·세션 spec 등에 파편화, OpenAPI로 표현 불가 | P5에서 해소 | 코드측 통일(이벤트 3종 artifact/gate/session) 완료, 본 PR의 @ws_protocol.md가 단일 레퍼런스 | §9-2 |
| 18 | **세션 수명주기 4종(heartbeat/resume/suspend/sessions) 프론트 소비 0건** — 백엔드 정책(O1)은 동작·테스트 보유, UI(O3)만 미구현 | 의도 보존(D4) | routers/session.py:1-69(4종 전부 response_model·summary, :3 "D4: UI 미연결" 주석 + server.py:35 태그 description) · 프론트 소비 0건 grep 확인 · O3 UI는 T2 백로그(spec §3) | §2 D4 |

## 2. 의도적 보존 항목과 사유 (9건 — 7번은 T3 P2 해소, 이력 기록)

T1이 **알면서 고치지 않은** 것들이다. 후속 작업자가 "버그인가?" 하고 다시 조사하는 낭비를 막기 위해 위치와 사유를 고정한다. §1 18건 중 상태가 '의도 보존'인 것은 18번(D4) 1건이며, 본 절의 9건은 18건 목록 밖에서 추가로 결정·발견된 보존 항목이다(7번은 이후 T3 P2가 해소 — 행 자체는 이력으로 유지).

| # | 항목 | 현행 위치 | 사유 |
| --- | --- | --- | --- |
| 1 | **step_status 어휘 혼재** — 'done'/'in_progress' vs 'PASS'/'WARN'/'BLOCKED' | brainstorming 'done'(harness_brainstorming.py:299) · design 'done'(gateway/pipeline.py:138 set_step_status — T3 P2 이동) · review 'in_progress'(:173)·PASS/WARN/BLOCKED(:585 · :614-616) · deploy 'in_progress'(routers/deploy.py:99)·'PASS'(:283, DispatchOut Literal schemas.py:202) · 프론트 탭 게이팅이 양 어휘 동시 의존(frontend/lib/cockpit-nav.ts:3·12·33) | spec §3 '기록만'. 변경 이득 대비 파급 큼 — 프론트 탭 게이팅 회귀 위험(D6 행동 보존) |
| 2 | **Passthrough 무기억** | harness.py:89-109 — 자체 상태 영속 없음, 멀티턴 맥락은 req.history만(:92-93), `_passthrough.md` 단일 노드 덮어쓰기(:107-109) | spec §3 — 멀티턴 기억은 신기능이므로 기록만(T1은 행동 보존 교정) |
| 3 | **advisor JSONL append race** | chat.py:31-34 `_append_event`(get_text→연결→put_text의 read-then-write) | spec §7-6 '기록만'. 같은 package_id 동시 턴 시 이벤트 소실 가능하나 현 UI는 카드 단위 순차 챗이라 비발생. 한 턴 내 다중 append(:57 · :74 · :86)는 단일 스레드 순차라 안전 |
| 4 | **server 팩토리 잔여 결합** | server.py(현행 102줄, 조립 전용) 내 `_provider_factory`(:82-83)·`_wrap_for_usage`(:85-87) 클로저(MarkerGateway 생성자 주입 :92-95 전용 소비) · 하위호환 re-export :19-20(test_owner_guard가 app.server 경유 import) · entitlement는 의도된 모듈 싱글턴(routers/deps.py:12-13 "app.state로 옮기지 말 것" — setenv→create_app fresh 의미론) | 클로저 2개는 게이트웨이 조립 전용으로 국소적, re-export·싱글턴은 테스트 의미론 보존 목적 |
| 5 | **entitlement.check() 잔존** | entitlement.py:39-41 — store 단독 판정(override 미반영), "신규 코드는 is_entitled 사용" 주석 | choke 위반(§1 표 4번) 재발 방지의 감시 대상으로 명시 유지 |
| 6 | **harness_design._parse_json 위임 셸** | harness_design.py:91-93(_parse_json)·:95-97(_load_references — T3 P2에서 동류 위임 셸 추가) | 구현은 core.parsing 단일본이므로 중복 아님(주석 명기). 기존 테스트 표면 보존 |
| 7 | **design state의 pending_ask 죽은 키** — **T3 P2 해소** | default에서 제외 + 로드 시 레거시 키 pop(harness_design.py:76) — 라이브 기존 run 호환은 pop이 담당 | P5 당시 '후속 정리 후보' → T3 P2(백로그 ⑤)에서 정리 완료. 본 행은 이력 기록 |
| 8 | **test_advisor_mode_branch 로컬 베이스라인** | tests/test_advisor_mode_branch.py:19-26 · :48 — env(ANTHROPIC_API_KEY) 의존 | 로컬 .env에 실키 존재 시 영구 실패(CI는 통과) — 알려진 로컬 베이스라인 |
| 9 | **state["gate"] vs 구 meta["gate"] 구분** | state["gate"] 소유는 T3 P2부터 gateway/pipeline.py(승인 :109-112·게이트 정지 :162-169 등)·셸은 _load_state 백필(harness_design.py:75)뿐 — `_state.json` 내부 파이프라인 상태(정지 step 기록)로 현행 설계 | P2가 제거한 것은 **응답 `meta["gate"]` wire 신호** — 이름이 같아 혼동 주의(둘은 별개 층위) |

## 3. 구 용어 → 현행 매핑 (이력 문서 독해용)

과거 spec·plan·설계문서(§4 참조)에 등장하는 구 용어를 현행 코드 어휘로 환산하는 표다.

| 구 (T1 P2 이전 / 이동 전) | 현행 |
| --- | --- |
| `AskPayload` | `GateEnvelope` kind="ask" |
| `HarnessResult.ask` · HTTP 응답 `ask` 키 | `gate` 필드 (응답 4키 `{output_path, text, gate, meta}`) |
| 응답 `meta["gate"]` | `gate` 봉투 |
| WS `{type:"askuser"}` | `{type:"gate"}` |
| WS `{kind:"restored"}` | `{type:"session", event:"restored", studio, run_id}` |
| `gateway/harness_advisor.py` `AdvisorHarness` | `deploy/advisor/chat.py` `DeployAdvisor` |
| `_ModelBoundProvider`·`_TrackedProvider` (server.py 내부) | `providers/wrappers.py` `ModelBoundProvider`·`TrackedProvider` (공개) |
| server.py 하네스 선택 if/elif | `gateway/registry.py` `select_harness` |
| `GatewayRun.action` 어휘 | **현행 Literal 5종 `advance`·`confirm`·`regenerate`·`restart`·`ack`** (routers/gateway.py:38) |
| 6요소 ABC 메서드(constraints·references·structured_output_schema·askuser_hook) | `PromptSpec`(gateway/prompt.py:12-30) — 죽은 ABC 메서드는 제거(§1 표 1번) |
| critic 반환 3종(str/list/dict) | `CriticVerdict`(gateway/critic.py:6-21) |
| `pendingAsk`(프론트 구 상태) | `applyGate` 단일 적용점+kind별 상태 3분배(CockpitProvider.tsx:393-413) |
| **— 이하 T3 P2/P3(2026-06-12) 추가 —** | |
| `DesignHarness.critic(scores)` | `gateway/design/scoring.py` `score_layout(scores)` (T1 백로그 ① — T3 P2) |
| `DesignHarness._run_critic` | `gateway/design/scoring.py` `run_critic` |
| `DesignHarness._s0_setup`~`_s3_final` 인라인 단계·제어 루프 | `gateway/design/steps.py` S0Setup~S3Final(PipelineStep) + `gateway/pipeline.py` PipelineOrchestrator(게이트 4분기·bypass 연쇄) |
| `DesignHarness._critic_gate` 단계 분기표 | 각 단계 `critic_gate` 메서드 + `GateCheck`(gateway/pipeline.py) |
| `harness_design.STEPS` 수기 튜플 | `gateway/design/steps.py` STEP_CLASSES 유도(STEPS·GATED_STEPS·CRITIC_STEPS :379-382) — harness_design은 동일 객체 re-export |
| design S3 critic 같은 턴 2회(run+gate 각 1회 채점) | `S3Final.run` 1회 채점 → `ctx.cache` 재사용(`critic_gate`) — T1 백로그 ②, P2 PR #65 |
| design S3 응답 `meta["step"]="done"` | `"S3"`(단계 name 상수화 — wire 불가시: 게이트 정지는 `_gate_result`가 step을 gate로 덮고 done 분기는 meta 신규 생성. P2 PR #65) |

> ⚠️ **stale 경고**: spec §4.2(:95)는 action 어휘에 "chat"을 표기하나 이는 stale(현행 어휘에서 소멸 — Literal 5종에 없음). 또한 `answer`는 action이 아니라 **별도 필드**다(routers/gateway.py:33 · :37 — ask 게이트 회신은 `answer` 필드로 보내는 wire 관례).

## 4. 구 경로 참조 잔존 문서 (갱신 비대상 — 시점 고정 원칙)

이력 문서는 작성 시점의 설계·계획 기록이므로 갱신하지 않는다. §3 매핑 표가 독해 혼동을 차단한다.

- **docs/specs · docs/plans 이력 문서 약 36파일 294건** (m3 plan 70건 · m3 spec 27건 · m6 plan 21건 등) — 시점 고정 원칙에 따라 무갱신.
- **docs/semi_stage/ 출품 초고 3건** (01_MVP_제안서 · 02_기능명세서:39·83 · 03_시연영상_콘티) — **출품물 제작 시 6요소→PromptSpec 어휘 교정 선행 필요** (후속 알림).
- **docs/eval/audit-plan.md:24 · rubric.md:90** — AskUser 훅의 WS 표현이 구식이나 저해 없음, 잔존. docs/eval/e2e-cost-plan.md는 P5-T2에서 경로 정정 완료.
- **docs/Refactor.md:44·93** — 사용자 기획 원문(무삭제 원칙)으로 갱신 비대상.
