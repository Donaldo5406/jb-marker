# DeployStudio 설계 (Deploy Studio — 규칙엔진 + 발송 어댑터)

> 대상: @Refactor.md §2-2-4 DeployStudio(64~65줄, **현재 비어 있음**).
> 성격: 다른 스튜디오와 달리 **AI 하네스가 아니다.** 결정론적 §50 규칙엔진 + 발송 어댑터(stub). 03 `deploy_plan.py`·`rules_engine.py` 재구조화.
> 짝 문서: @review_subharness.md(경계 구분), @marker_api.md(오케스트레이션·VfsStore), @navigate.md(진입 게이트), @vfs.md(폴더).
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화. 점검 보고서 @harness_audit.md

---

## 0. 전제 — 왜 하네스가 아닌가

- **결정론적**: §50 판정(`rules_engine.py`의 `evaluate_recipient`)은 LLM이 아니라 **순수 규칙 로직**. 다른 스튜디오는 "AI가 창작/검토"라 Marker 하네스가 필요했지만, DeployStudio 핵심은 **규칙엔진 + 발송 어댑터**다. → 하네스 6요소 프레임 미적용.
- **진입 게이트**: review가 PASS여야 진입(@navigate.md③ — critical이면 deploy 탭 잠금). 즉 **콘텐츠 적법성은 이미 통과**한 상태 → DeployStudio는 **발송 행위 적법성 + 발송 준비**만 얹는다.
- **외부 실연동은 stub**: 03 `deploy_plan.py:9` 명시 — "C7 deploy adapter is STUB — real channel dispatch is Out-of-scope." MVP도 동일(어댑터 자리만, 시뮬/export).
- **하네스는 없지만 advisory 챗은 있음**: 결정론적 §50 결과를 **바꾸지 않는** 비권위적 조언자. 구현=**DeployAdvisor**(`backend/app/deploy/advisor/chat.py:18` — T1-P1에서 `gateway/harness_advisor.py`의 AdvisorHarness를 이동·개명, 독스트링 :1-5 "하네스가 아니다"). Harness ABC 미상속·게이트웨이 비경유 — '하네스 아님' 선언과 코드 명명이 정합해짐. 창작/검토 산출을 내는 하네스와 구분 — §7.

## 1. ReviewStudio와의 경계 (겹침=착시)

둘 다 "법률"을 보지만 **검토 대상이 다르다.** 03도 이미 다른 룰셋으로 분리돼 있다.

| | ReviewStudio | DeployStudio |
|---|---|---|
| 질문 | 내용이 합법인가 | 누구에게·언제·어떻게 보내는가가 합법인가 |
| 대상 | 콘텐츠(카피·비주얼·과장·필수고지·다국어 동등성) | 발송 행위(동의·야간·옵트아웃·채널) |
| 근거법 | 표시광고법·금융광고규제(`rules_marketing.yaml`) | **다중 정책 합성**: 정보통신망법 §50(`policies/infomatics.yaml`) + 개인정보보호법 §15·§16(`policies/pipa.yaml`) |
| 입력 | `metadata.md`(텍스트+콘티) | `consent_ledger`(수신자) + 발송시간 + 채널 |

- 유일한 인접점: "필수 고지가 콘텐츠에 **존재**하는가"=Review / "그 고지를 붙여 **발송**하는 행위"=Deploy. 중복 아님.

## 2. 입출력 (@vfs.md 계약)

- **입력**: `design/final/{lang}`(확정 산출물·구조화 씬) + `design/metadata.md` + `plan.md`(채널·언어·발송정책 시드) + `consent_ledger`(수신자 동의 원장).
- **출력**: `/{runId}/deploy/`(@vfs.md deploy 자리 채움 — 구현 폴더 트리는 §5, **평면 `{channel}_{lang}` package_id** 구조).

## 3. 파이프라인 (D0 → D3)

```
D0 셋업      design/final + metadata.md + plan.md + consent_ledger 로드
             채널 × 언어 매트릭스 산출

D1 발송 적법성  다중 정책 규칙엔진(evaluate_recipient · 결정론적 · LLM 아님)
   (§50+pipa)   policies/infomatics.yaml(§50): opt_out / 무동의(동종상품 6개월 예외) / 야간(21~08)
             + policies/pipa.yaml(개인정보보호법 §15·§16): purpose_violation / retention_expired
             정책별 평가 합성 — 가장 강한 BLOCK 채택(_BLOCK_PRIORITY(deploy/rules_engine.py:13-19)·합성 평가(:56-87))
             → 발송대상 · 제외목록(사유+법 인용) · 정책별 breakdown(routers/deploy.py:140) · 24시간 캘린더
             → deploy/eligibility/

D2 채널 패키징  채널별 규격(이미지 사이즈·카피 길이·필수고지)에 맞춰 export
             구조화 씬(@design_subharness.md A안)이라 언어·채널별 리사이즈 export 가능
             얇은 LLM 보조 = 채널별 카피 적응 — 미결→**채택 확정**(DeployAdvisor·§7,
             Review 통과 텍스트·grounding 불변 계약은 grounding.check로 강제)
             → deploy/packages/{channel}_{lang}/ (평면 package_id — 중첩 {channel}/{lang}/ 아님)

D3 발송 어댑터  DeployAdapter 인터페이스 호출 (MVP = StubAdapter)
   (STUB)      시뮬레이션: 발송 예약 미리보기 + export 패키지 다운로드
             실제 채널 dispatch는 어댑터 자리만 — 추후 실연동 스왑

게이트       정책 제외 대상은 BLOCK이 아니라 **필터**(제외하고 발송).
             최종 발송은 **사용자 확정 게이트**(confirm) — 자동 발송 안 함.
             dispatch 가드 순서: require_owner → confirmed(400 'user confirm required')
             → is_entitled(402) → 수신자/채널 빈값(400) (routers/deploy.py:217-234)
```

- D1은 순수 함수라 그래프/하네스 불필요(@marker_api.md §2 — LangGraph 미사용과 정합).

### 3-1. D단계 ↔ 라우트 매핑 (`routers/deploy.py` — 전부 require_owner)

| 단계 | 라우트 | 위치 |
|---|---|---|
| D0 | `POST /runs/{run_id}/deploy/setup` | routers/deploy.py:83 |
| D1 | `POST /runs/{run_id}/deploy/eligibility` | :103 |
| D2 | `POST /runs/{run_id}/deploy/packages` + `POST …/deploy/advisor/chat` | :144 · :183 |
| D3 | `POST /runs/{run_id}/deploy/dispatch` | :213 |
| 보조 | `POST …/deploy/demo-payment` · `GET …/deploy/_state` | :287 · :297 |

- advisor 응답 계약: live LLM의 `_usage`는 `record_usage(step="advisor")`로 영속한 후 **`_usage`/`_model`을 HTTP 응답에서 pop**(:199-209, P1 표면 위생).

## 4. 발송 어댑터 (stub → 실연동 스왑)

- `DeployAdapter` 인터페이스: `dispatch(channel, package: Package, schedule: ScheduleSpec, recipients: list[dict]) -> DispatchResult` + `status` 프로퍼티(stub|live)(`deploy/adapters/base.py:34-42`).
- **MVP impl = StubAdapter**: 실제 발송 없이 시뮬레이션. `config.deploy_adapter_mode`는 **부재** — stub 여부는 `adapters/registry.py`(현재 6개 provider 전부 StubAdapter) + `providers.yaml`의 `adapter_status` 필드로 표현. config 실존 키: `advisor_mode`·`anthropic_advisor_model`·`entitlement_override`.
- **추후 impl**: 채널별(이메일 SMTP, 카카오 알림톡, 광고플랫폼 등) — 인터페이스 뒤에서 교체.
- **프로바이더 레지스트리**: 각 프로바이더 = `{id, 이름, SVG 로고, 채널유형, 어댑터 상태(stub/live), 필요 크리덴셜}`. 프론트가 **로고 그리드**로 렌더(Refactor 21줄 '연동가능한 앱' 메뉴와 동일 소스). 프로바이더 1개 = 어댑터 impl 1개(현재 전부 stub). 사용자가 발송 대상 채널 선택 → D2가 선택 채널만 패키징.
- @marker_api.md의 `VfsStore` 추상화와 **동형 패턴**(인터페이스 고정 + 백엔드 스왑) → 락인 없음.

## 5. 가상 폴더 (@vfs.md deploy/ 채움)

```
/{runId}/deploy/
  inputs/                                  # D0: selected_providers.json · matrix.json (routers/deploy.py:91-98)
  eligibility/                             # D1: recipients.json · excluded.json · calendar.json (:124-135)
  packages/{channel}_{lang}/               # D2: 평면 package_id 디렉터리 — copy.md · copy.meta.json · package.meta.json (:158-179)
  advisor/transcripts/{package_id}.jsonl   # D2: 어드바이저 챗 transcript (chat.py:28-29)
  dispatch/                                # D3: plan.json · simulation.json (:269-276)
  report.md                                # D3: 발송 계획·시뮬 결과 종합
```

- packages는 **평면** `{channel}_{lang}` package_id 디렉터리 — 중첩 `{channel}/{lang}/` 아님.
- export ZIP·씬 리사이즈는 **백엔드 미구현** — ZIP은 프론트 `lib/deployExport`가 담당.

## 6. 기존 자산 재사용 / 변경점

- **재사용**: `rules_engine.py`(다중 정책 엔진 — §50+pipa), `evaluate_recipient`, `deploy_plan_node` 로직(캘린더·제외 산출). `config.deploy_adapter_mode`는 **재사용 안 함**(키 자체가 부재 — §4).
- **변경**: `deploy_plan` 결과를 PlanState가 아니라 **VFS `deploy/`에 영속**(VfsStore.put) / 채널 export = 구조화 씬 리사이즈로 신설 / StubAdapter 인터페이스 명시.

## 7. 프론트 표면 — 프로바이더 SVG + 발송 어드바이저 챗

- **프로바이더 SVG 나열**: 외부 가용 프로바이더를 **SVG 로고 그리드**로 노출(레지스트리 §4). 각 로고 = 선택 가능한 발송 채널 + 어댑터 상태 배지(stub/실연동). Refactor 21줄 '연동가능한 앱'과 동일 소스.
- **발송 어드바이저 챗**: 구현=**DeployAdvisor**(`backend/app/deploy/advisor/chat.py:18` — T1-P1에서 `gateway/harness_advisor.py`의 AdvisorHarness를 이동·개명). **Marker 하네스 아님**(Harness ABC 미상속·게이트웨이 비경유). 모듈 구성: `chat.py`(본체) · `prompt.py`(SYSTEM_PROMPT) · `tools.py`(도구 화이트리스트) · `grounding.py`(check) · `scripted.py`(ScriptedAdvisorProvider — P4 분리) · `live.py`(AnthropicAdvisorProvider). **유료 티어 $100/월 전용 — Refactor C4**.
  - **엔타이틀먼트**: deploy 표면은 `app/entitlement.py` `is_entitled(user_id)` 단일 choke(P1) — advisor chat 402(routers/deploy.py:191-192) + **dispatch에도 402**(:222-223). demo-payment가 set_dev_pass 부여(:287-294), GET _state가 dev_pass(=is_entitled) 노출(:311). ⚠️ `gateway/entitlement.py`의 `check_entitlement(is_marker, override)`는 gateway 마커 게이트용 **별개 함수** — 혼동 금지.
  - **읽기 범위 = 도구 3종 한정**: `read_review`(packages/{id}/copy.meta.json) · `read_eligibility`(eligibility/recipients.json 요약 — eligible_count·languages만) · `write_d2_copy`(tools.py:11 ALLOWED · :14-41 TOOL_SCHEMAS, 구현 chat.py:36-51). 캘린더·선택 채널·`plan.md`·`metadata.md` 직접 읽기는 **미구현**. 역할=D2 채널 규격 카피 적응이 1차(prompt.py:3-6) + 조언.
  - **쓰기 경계**: 유일한 쓰기 표면=`write_d2_copy`(적응 카피 — grounding.check 통과 시에만 copy.md+copy.meta.json 영속, chat.py:96-123). §50 판정·dispatch·Review 원문 변경은 도구 부재 + 프롬프트 금지 조항(prompt.py:8-12)으로 차단 — **비권위 경계는 유지되나 표면이 '조언만'은 아님**(규칙엔진=진실, 콘텐츠 원문=Review/Design 소관). 실행(발송)은 사용자 확정 게이트(D3).
  - **프로바이더 3모드**: mock=true→ScriptedAdvisorProvider 강제(LLM 없음·시연) / ADVISOR_MODE=live(키 필수, 없으면 422) 또는 auto+키 보유→AnthropicAdvisorProvider / 그 외 scripted 폴백(routers/deploy.py:60-79 `_make_advisor_provider`). 프롬프트는 PromptSpec(persona=SYSTEM_PROMPT, studio="deploy", step="advisor_chat") 조립(chat.py:63-72 — meta는 provider.chat 미지원으로 현재 미전달, 코드 주석 명기).
- 다른 스튜디오의 멀티턴 챗 UI(@brainstorm_subharness.md②)와 동일 표면을 재사용하되 **advisory 모드**(하네스 아님 — 구현=DeployAdvisor, §0·본 절).

## 미결 / 후속 결정 항목 (T1 교정 후 상태)

해소(구현으로 결정 확정):
- ~~① **채널별 규격 카탈로그** 출처~~ → **해소**: `providers.yaml` 내 provider별 `spec`(image_sizes·copy_limits·required_disclosures).
- ~~② D2 카피 적응 **LLM 보조 사용 여부**~~ → **채택**: DeployAdvisor `write_d2_copy`(§7) — Review 통과 텍스트·grounding 불변 계약은 grounding.check로 강제.
- ~~③ `consent_ledger` 출처~~ → **해소**: 데모 fixture(`deploy/consent_ledger.json` · `ledger.py`).
- ~~⑤ §50 외 추가 발송규제 **확장 여부**~~ → **해소**: 개인정보보호법 채택(`policies/pipa.yaml` §15·§16) — 다중 정책 합성(§1·D1).
- ~~⑥ 어드바이저 챗 **권한 경계 강제 방식**~~ → **해소**: 도구 화이트리스트(ALLOWED(tools.py:11)+assert_allowed(:44-46)) + grounding.check + 프롬프트 금지 조항(prompt.py:8-12).
- ~~⑦ 프로바이더 레지스트리 **소스/스키마**~~ → **해소**: `providers.yaml` + Pydantic `Provider` 모델(id·name·logo_path·channel_type·adapter_status·priority·credentials_schema·spec — `deploy/providers.py:11-43`).

잔존:
- ④ `DeployAdapter` 실연동 채널 **우선순위**(+규격 카탈로그 외부 출처 검증).
