# ReviewStudio 하네스 설계 (Review Sub-harness)

> 대상: @Refactor.md §2-2-3 ReviewStudio(56~60줄) + §백기획 Marker 하네스(67줄).
> 착안: mvp 02 준법검토(**02 코드/문서는 비참조**) + mvp 03 `review.py`·`i18n_equiv.py` **재구조화**.
> 짝 문서: @design_subharness.md·@brainstorm_subharness.md. 폴더 SSOT: @vfs.md.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: jb-marker 코드(backend/app·frontend)
> 갱신: 2026-06-11 — T1 교정(P1~P4) 반영, 구현 동기화(spec §9-3 목록 외 가산 — P5 조사에서 동질 괴리 확증). 점검 보고서 @harness_audit.md

---

## 0. 명세 ↔ 03 현황 ↔ 결정

| 명세 | 03 현황 (설계 당시 03 현황 — 역사 기록, 인용 파일은 현 레포 부재) | 결정 |
|---|---|---|
| 1. 법률 서칭(공식문서만) | `review.py` 정적 룰셋(`rules_marketing.yaml`+corpus_snapshot) — 서칭 없음 | LLM **동적 서칭 + 공식 법령 source 화이트리스트** 승격 |
| 2. 법률 검토 페르소나 | `ComplianceEngine.verify` 룰셋 기반 | **LLM 전문 페르소나** 승격 |
| 3. 동등성 페르소나 | `i18n_equiv.py` 키워드 매핑(정적 `DISCLOSURE_I18N`) | **LLM 전문 페르소나** 승격 |
| 4. 통합 최종 검토(race) | 없음 (review→i18n 순차, 조정 부재) | **reconciler 신규**(R3) |
| 5. 권장만, 수정 X | `remediation.fix_block_assets`·`creative_reviser` = 자동 수정 | **수정 분리** — ReviewStudio는 권장만 |
| 6. iteration | `review.py` 멱등 재구축(재검토 시 stale verdict 교체) | **full 재검토 루프** 채택 |
| 7. critical BLOCK / warning pass | 게이트 동작(`BLOCK→BLOCKED`, `test_gate_warn_pass_through`) | **GateEnvelope(kind="status") 봉투로 발신** — compute_gate(BLOCKED/WARN/PASS + 5트리거 강등). **기존 'warning→pass' 단순 통과 서술은 부정확 — WARN은 ack 필요**. i18n에도 critical 도입 |

> 03 인용은 역사 기록 — 이식 사실은 코드에 남음: `backend/app/core/severity.py:1` 헤더가 "03 nodes/i18n_equiv.py 이식+M5 강화"로 기록.

---

## ① 검토 파이프라인 (3 페르소나 + 게이트)

- **입력**: 카피 = `design/final/{lang}/main.scene` 복원 + `layout.spec.json[copy][lang]` 폴백(backend/app/gateway/harness_review.py:218-249 — @design_subharness.md cross-actor 계약) + `design/metadata.md`(텍스트+콘티) + `plan.md` frontmatter(languages·disclosures). 추가 입력: `design-system/components/visual/v1.png` · `review/_render/{lang}.png` matrix(:156-162).
- **출력**: `review/{legal, i18n, revise, report.md}` — **권장만, 수정하지 않음**.

```
R0 셋업    plan.md frontmatter의 languages를 정규화해 사용 — multinational 플래그 미사용(:143-146)
           멱등 cleanup 후 검토 매트릭스(언어별 scene/render + 컴포넌트, :156-162)

R1 법률 검토 (페르소나 A — 전문 법률 검토관) — 4갈래
           호출0 = 결정론 시각 적법성 룰(core/visual_rules — layout.spec.json의
                   글자크기·대비·고지 검사, 비전 LLM 무관, harness_review.py:261-277)
           호출1 = 텍스트 + 동적 법령 서칭(search_and_filter — 공식 법령 화이트리스트 필터, :280-299)
           호출2 = 컴포넌트 단독 비전(design-system/components/visual/v1.png, :302-335)
           호출3 = 언어별 합성 렌더 비전(review/_render/{lang}.png — 프론트가 Fabric 씬을
                   PNG로 렌더해 업로드하는 cross-actor 입력(frontend/lib/sceneRender.ts:66·
                   CockpitProvider.tsx:494-517), :337-372)
           위반 포인팅: 자산 / 위치 / 조항 → review/legal/law_{id}/
           severity: critical | warning · 비전 실패는 graceful(vision_failed/vision_skipped → WARN 강등)
           영상(video) 검수는 미구현

R2 동등성 검토 (페르소나 B — 전문 다국어 동등성 검토관)
           활성 = len(languages) > 1 AND 'ko' 포함 (아니면 r2_skipped=mono-lingual, :388-396)
           LLM 판정 + 키워드 안전망 이중 검출(find_missing_disclosures·DISCLOSURE_I18N —
           core/severity.py:11-49 · LLM 없이도 missing_disclosure는 critical, :451-468)
           언어별 비교: 필수고지 보존 · 오역 · 과장 · 누락 → review/i18n/reason_{id}/
           severity: critical(missing_disclosure는 강제 critical, :437-440) | warning

R3 통합 검토 (페르소나 C — reconciler)            ← 신규(명세 4)
           A·B 권장 충돌(race) 조정
             예) 법률상 문구 추가 요구 ↔ 동등성상 간결화 요구 충돌
           중복 제거 · 우선순위 · 일관성 → review/revise/{image,text,video}/ + report.md

게이트     게이트 신호 = GateEnvelope(kind="status") — R3가 compute_gate
           (backend/app/core/severity.py:52-91 — BLOCKED/WARN/PASS 판정 + 5트리거 PASS→WARN 강등:
            live_unavailable·parse_failed·vision_failed·step_failed·vision_skipped) 결과를
           status·critical_count·warning_count·actions=_actions_for
           (backend/app/gateway/harness_review.py:42-48 테이블: WARN→[ack,regenerate,restart]·
            BLOCKED→[regenerate,restart]·PASS→[])로 발신(:594-597)
           기존 'warning→pass' 단순 통과 서술은 부정확 — WARN은 ack 필요(사용자 확인 후
           deploy 해제, state.acknowledged · WARN 외 상태에서 ack 무시, :613-630)
           manifest step_status 기록(:585)은 유지되나 wire 계약은 봉투
```

- 비전 AI = **Gemini**(생성 시 주입된 vision_provider — harness_review.py:4·:74-75). R1 호출2(컴포넌트 단독)·호출3(언어별 합성 렌더) 2패스로 시각적 위반을 검수. 비전 실패는 graceful: vision_failed/vision_skipped 플래그 → PASS→WARN 강등. **영상(video) 검수는 미구현**.
- 페르소나 조립: 3 페르소나(PERSONA_A/B/C, harness_review.py:53-69)는 PromptSpec(persona, studio="review", step="R1/R2/R3")로 조립되어 provider.complete(system=assemble(), meta=) 전달(:411-414·:498-501) — meta가 DemoProvider 단계 감지 계약. R1 텍스트 패스는 search_and_filter에 meta 직접 명시(:282-284).
- wire 상세 @ws_protocol.md — 주의: review status 게이트는 HTTP 응답 gate 전용(WS gate 이벤트는 brainstorming만).

## ② Iteration 루프 (명세 6)

`report.md` 권장 → 사용자가 **DesignStudio에서 수정**(ReviewStudio는 수정 안 함) → 재검토 = action "restart" → **R0부터** full 재실행(harness_review.py:98-100·:600-611). 수정이 새 문제를 유발할 수 있으므로 증분이 아닌 **full 재검토**. `_cleanup_review_tree`(:125-136)가 `legal/`·`i18n/`·`revise/`·`report.md` 삭제(`_render/`·`_state.json`은 보존)로 멱등을 보장해 stale BLOCK이 살아남지 않음. 구동 모델: gateway 1호출 = 1 step 전진, 프론트 runReview가 done까지 루프(CockpitProvider.tsx:494-499).

## ③ 수정 분리 (명세 5 — 03으로부터의 변경점)

- ReviewStudio = `revise/` **권장만** 기록. design 폴더를 수정하지 않음.
- 03의 자동 수정(`remediation.fix_block_assets`, `creative_reviser`)은 **ReviewStudio 책임에서 제거** → DesignStudio(또는 사용자 수동 액션)로 귀속(미결).

## ④ 하네스 6요소 (다른 하네스와 대칭)

| 요소 | 내용 |
|---|---|
| 시스템 프롬프트 | 3 페르소나(법률 검토관 A · 동등성 검토관 B · 통합 reconciler C) |
| 제약/토큰 | 공식 법령 문서만(서칭 화이트리스트) · severity 규칙(critical→BLOCKED / WARN은 ack 필요 / PASS — §① 게이트) |
| 레퍼런스 | 서칭된 공식 법률 + `metadata.md` + 필수고지 마스터 |
| 구조화 출력 | `legal/` `i18n/` `revise/` `report.md` (포인팅 구조) |
| 크리틱/통합 | R3 reconciler(race 조정) |
| AskUser 훅 | review에 ask 게이트 없음 — 후속 상호작용은 status 봉투의 actions(ack/regenerate/restart)로만(harness_review.py:96-104) |
| (+) 공유 스킬 | 파일시스템 CRUD + **비전 AI 검수(Gemini)** |

## ⑤ 가상 폴더 (vfs.md `review/` 발췌)

```
/{runId}/review/
  legal/law_{id}/verdict.json    # R1: 위반 법률별 포인팅 — verdict 봉투
  i18n/reason_{id}/verdict.json  # R2: 동등성 사유별 — verdict 봉투
  revise/{image,text,video}/rec_{sha1[:8]}.md  # R3: 최종 권장(target 비정상값은 text로 정규화, :514-528)
  report.md            # 종합 — frontmatter에 gate status/counts/flags(:539-552)
  _render/{lang}.png   # 프론트 업로드(합성 렌더 비전 입력 — cross-actor)
  _state.json          # 하네스 step state
```

- verdict.json 봉투 키: `verdict_id`·`node`·`asset_id`·`lang`·`severity`·`location`·`evidence`·`audit_trace_id`·`created_at` + 선택 `clause`·`official_source_url`·`kind`·`disclosure`(harness_review.py:181-216).

## 미결 / 후속 결정 항목 (2026-06-11 — 3건 해소)

- ~~공식 법령 **서칭 소스** 구체화(법령 DB·화이트리스트)~~ → **해소**: `core/legal_search`(load_whitelist·apply_whitelist·search_and_filter) — 공식 법령 화이트리스트.
- 자동 수정 로직 **귀속처**(DesignStudio reviser로 이동 여부) — 미결 유지.
- ~~AskUser **bypass 세부**~~ → **해소**: `_actions_for` 테이블(harness_review.py:42-48) + ack는 WARN 전용(BLOCKED는 ack 불가 — regenerate/restart만).
- ~~verdict **severity 스키마**~~ → **해소**: verdict.json 봉투(harness_review.py:181-216) + missing_disclosure 강제 critical(:437-440) + 5트리거 강등(core/severity.py:66-91).
