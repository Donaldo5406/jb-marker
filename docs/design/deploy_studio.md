# DeployStudio 설계 (Deploy Studio — 규칙엔진 + 발송 어댑터)

> 대상: @Refactor.md §2-2-4 DeployStudio(64~65줄, **현재 비어 있음**).
> 성격: 다른 스튜디오와 달리 **AI 하네스가 아니다.** 결정론적 §50 규칙엔진 + 발송 어댑터(stub). 03 `deploy_plan.py`·`rules_engine.py` 재구조화.
> 짝 문서: @review_subharness.md(경계 구분), @marker_api.md(오케스트레이션·VfsStore), @navigate.md(진입 게이트), @vfs.md(폴더).
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 (01·02 비참조)

---

## 0. 전제 — 왜 하네스가 아닌가

- **결정론적**: §50 판정(`rules_engine.py`의 `evaluate_recipient`)은 LLM이 아니라 **순수 규칙 로직**. 다른 스튜디오는 "AI가 창작/검토"라 Marker 하네스가 필요했지만, DeployStudio 핵심은 **규칙엔진 + 발송 어댑터**다. → 하네스 6요소 프레임 미적용.
- **진입 게이트**: review가 PASS여야 진입(@navigate.md③ — critical이면 deploy 탭 잠금). 즉 **콘텐츠 적법성은 이미 통과**한 상태 → DeployStudio는 **발송 행위 적법성 + 발송 준비**만 얹는다.
- **외부 실연동은 stub**: 03 `deploy_plan.py:9` 명시 — "C7 deploy adapter is STUB — real channel dispatch is Out-of-scope." MVP도 동일(어댑터 자리만, 시뮬/export).
- **하네스는 없지만 advisory 챗은 있음**: 결정론적 §50 결과를 **바꾸지 않는** 비권위적 조언자(채널 믹스·허용 시간대 내 타이밍·타게팅 전략). 창작/검토 산출을 내는 하네스와 구분 — §7.

## 1. ReviewStudio와의 경계 (겹침=착시)

둘 다 "법률"을 보지만 **검토 대상이 다르다.** 03도 이미 다른 룰셋으로 분리돼 있다.

| | ReviewStudio | DeployStudio |
|---|---|---|
| 질문 | 내용이 합법인가 | 누구에게·언제·어떻게 보내는가가 합법인가 |
| 대상 | 콘텐츠(카피·비주얼·과장·필수고지·다국어 동등성) | 발송 행위(동의·야간·옵트아웃·채널) |
| 근거법 | 표시광고법·금융광고규제(`rules_marketing.yaml`) | **정보통신망법 §50**(`infomatics_policy.yaml`) |
| 입력 | `metadata.md`(텍스트+콘티) | `consent_ledger`(수신자) + 발송시간 + 채널 |

- 유일한 인접점: "필수 고지가 콘텐츠에 **존재**하는가"=Review / "그 고지를 붙여 **발송**하는 행위"=Deploy. 중복 아님.

## 2. 입출력 (@vfs.md 계약)

- **입력**: `design/final/{lang}`(확정 산출물·구조화 씬) + `design/metadata.md` + `plan.md`(채널·언어·발송정책 시드) + `consent_ledger`(수신자 동의 원장).
- **출력**: `/{runId}/deploy/`(@vfs.md deploy 자리 채움).

## 3. 파이프라인 (D0 → D3)

```
D0 셋업      design/final + metadata.md + plan.md + consent_ledger 로드
             채널 × 언어 매트릭스 산출

D1 발송 적법성  §50 규칙엔진(03 evaluate_recipient 재사용 · 결정론적 · LLM 아님)
   (§50)       수신자별 판정: opt_out / 무동의(동종상품 6개월 예외) / 야간(21~08) / 허용
             → 발송대상 · 제외목록(사유+법 인용) · 24시간 캘린더(야간 차단)
             → deploy/eligibility/

D2 채널 패키징  채널별 규격(이미지 사이즈·카피 길이·필수고지)에 맞춰 export
             구조화 씬(@design_subharness.md A안)이라 언어·채널별 리사이즈 export 가능
             (선택) 얇은 LLM 보조 = 채널별 카피 적응 — 단 Review 통과 텍스트·grounding 불변
             → deploy/packages/{channel}/{lang}/

D3 발송 어댑터  DeployAdapter 인터페이스 호출 (MVP = StubAdapter)
   (STUB)      시뮬레이션: 발송 예약 미리보기 + export 패키지 다운로드
             실제 채널 dispatch는 어댑터 자리만 — 추후 실연동 스왑

게이트       §50 제외 대상은 BLOCK이 아니라 **필터**(제외하고 발송).
             최종 발송은 **사용자 확정 게이트**(confirm) — 자동 발송 안 함.
```

- D1은 순수 함수라 그래프/하네스 불필요(@marker_api.md §2 — LangGraph 미사용과 정합).

## 4. 발송 어댑터 (stub → 실연동 스왑)

- `DeployAdapter` 인터페이스: `dispatch(channel, package, schedule) -> result`.
- **MVP impl = StubAdapter**: 실제 발송 없이 로그·미리보기·export ZIP. (03 `config.deploy_adapter_mode="stub"` 재사용.)
- **추후 impl**: 채널별(이메일 SMTP, 카카오 알림톡, 광고플랫폼 등) — 인터페이스 뒤에서 교체.
- **프로바이더 레지스트리**: 각 프로바이더 = `{id, 이름, SVG 로고, 채널유형, 어댑터 상태(stub/live), 필요 크리덴셜}`. 프론트가 **로고 그리드**로 렌더(Refactor 21줄 '연동가능한 앱' 메뉴와 동일 소스). 프로바이더 1개 = 어댑터 impl 1개(현재 전부 stub). 사용자가 발송 대상 채널 선택 → D2가 선택 채널만 패키징.
- @marker_api.md의 `VfsStore` 추상화와 **동형 패턴**(인터페이스 고정 + 백엔드 스왑) → 락인 없음.

## 5. 가상 폴더 (@vfs.md deploy/ 채움)

```
/{runId}/deploy/
  eligibility/       # D1: §50 판정 — 발송대상·제외(사유+법인용)·24시간 캘린더
  packages/          # D2: 채널별 규격 export
    {channel}/{lang}/   #   이메일/인스타/알림톡/배너 × 언어, + 발송 메타
  report.md          # D3: 발송 계획·시뮬 결과·어댑터 상태 종합
```

## 6. 기존 자산 재사용 / 변경점

- **재사용**: `rules_engine.py`(§50 엔진), `evaluate_recipient`, `deploy_plan_node` 로직(캘린더·제외 산출), `config.deploy_adapter_mode`.
- **변경**: `deploy_plan` 결과를 PlanState가 아니라 **VFS `deploy/`에 영속**(VfsStore.put) / 채널 export = 구조화 씬 리사이즈로 신설 / StubAdapter 인터페이스 명시.

## 7. 프론트 표면 — 프로바이더 SVG + 발송 어드바이저 챗

- **프로바이더 SVG 나열**: 외부 가용 프로바이더를 **SVG 로고 그리드**로 노출(레지스트리 §4). 각 로고 = 선택 가능한 발송 채널 + 어댑터 상태 배지(stub/실연동). Refactor 21줄 '연동가능한 앱'과 동일 소스.
- **발송 어드바이저 챗**: 발송 계획을 **조언**하는 AI 챗(일반 Claude — **Marker 하네스 아님**, **유료 티어 $100/월 전용 — Refactor C4**, 엔타이틀먼트 검사=@marker_api.md §3-2).
  - 읽음: §50 eligibility 결과 · 캘린더 · 선택 채널 · `plan.md` · `metadata.md`.
  - 조언: 채널 믹스 추천 · **허용 시간대 내** 발송 타이밍 · 제외 대상 해석 · 도달/예산 전략.
  - **비권위적 경계**: §50 판정·발송 여부·콘텐츠를 **바꾸지 않는다**(규칙엔진=진실, 콘텐츠=Review/Design 소관). 조언만, 실행은 사용자 확정 게이트(D3).
- 다른 스튜디오의 멀티턴 챗 UI(@brainstorm_subharness.md②)와 동일 표면을 재사용하되 **advisory 모드**(하네스 아님).

## 미결 / 후속 결정 항목

- **채널별 규격 카탈로그** 출처(사이즈·카피 제약·필수고지 매핑).
- D2 카피 적응에 **LLM 보조 사용 여부**(쓰면 Review 통과 텍스트·grounding 불변 계약 필요).
- `consent_ledger` 출처(데모 fixture vs 실제 마이데이터/CRM 연동).
- `DeployAdapter` 실연동 채널 **우선순위**.
- §50 외 추가 발송규제(개인정보보호법 등) **확장 여부**.
- 어드바이저 챗 **권한 경계 강제 방식**(조언만 — §50·발송·콘텐츠 변경 불가를 어떻게 보장).
- 프로바이더 레지스트리 **소스/스키마**(SVG 로고·채널유형·필요 크리덴셜 카탈로그).
