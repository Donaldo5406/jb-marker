# ReviewStudio 하네스 설계 (Review Sub-harness)

> 대상: @Refactor.md §2-2-3 ReviewStudio(56~60줄) + §백기획 Marker 하네스(67줄).
> 착안: mvp 02 준법검토(**02 코드/문서는 비참조**) + mvp 03 `review.py`·`i18n_equiv.py` **재구조화**.
> 짝 문서: @design_subharness.md·@brainstorm_subharness.md. 폴더 SSOT: @vfs.md.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing 코드 + docs/03 (01·02 비참조)

---

## 0. 명세 ↔ 03 현황 ↔ 결정

| 명세 | 03 현황 (코드 근거) | 결정 |
|---|---|---|
| 1. 법률 서칭(공식문서만) | `review.py` 정적 룰셋(`rules_marketing.yaml`+corpus_snapshot) — 서칭 없음 | LLM **동적 서칭 + 공식 법령 source 화이트리스트** 승격 |
| 2. 법률 검토 페르소나 | `ComplianceEngine.verify` 룰셋 기반 | **LLM 전문 페르소나** 승격 |
| 3. 동등성 페르소나 | `i18n_equiv.py` 키워드 매핑(정적 `DISCLOSURE_I18N`) | **LLM 전문 페르소나** 승격 |
| 4. 통합 최종 검토(race) | 없음 (review→i18n 순차, 조정 부재) | **reconciler 신규**(R3) |
| 5. 권장만, 수정 X | `remediation.fix_block_assets`·`creative_reviser` = 자동 수정 | **수정 분리** — ReviewStudio는 권장만 |
| 6. iteration | `review.py` 멱등 재구축(재검토 시 stale verdict 교체) | **full 재검토 루프** 채택 |
| 7. critical BLOCK / warning pass | 게이트 동작(`BLOCK→BLOCKED`, `test_gate_warn_pass_through`) | 재사용 + **i18n에도 critical 도입** |

---

## ① 검토 파이프라인 (3 페르소나 + 게이트)

- **입력**: `design/final/{lang}` + `design/metadata.md`(텍스트+콘티) + `plan.md`(다국어 플래그·필수고지).
- **출력**: `review/{legal, i18n, revise, report.md}` — **권장만, 수정하지 않음**.

```
R0 셋업    design 산출물 + metadata.md + plan.md 로드
           검토 매트릭스(자산 × 언어). 다국어 플래그 → R2 활성

R1 법률 검토 (페르소나 A — 전문 법률 검토관)
           관련 법률 동적 서칭 (공식 법령 문서만 · source 화이트리스트)
           위반 포인팅: 자산 / 위치 / 조항 → review/legal/law_xxxx/
           이미지·영상 = metadata.md + 비전 AI(Gemini) 검수 (Refactor 58줄)
           severity: critical | warning

R2 동등성 검토 (페르소나 B — 전문 다국어 동등성 검토관) · 다국어일 때만
           언어별 비교: 필수고지 보존 · 오역 · 과장 · 누락 → review/i18n/reason_xxx/
           severity: critical(필수고지 누락 등) | warning

R3 통합 검토 (페르소나 C — reconciler)            ← 신규(명세 4)
           A·B 권장 충돌(race) 조정
             예) 법률상 문구 추가 요구 ↔ 동등성상 간결화 요구 충돌
           중복 제거 · 우선순위 · 일관성 → review/revise/{image,video}/ + report.md

게이트     critical 1개라도 → BLOCK (manifest.step_status.review=BLOCKED, deploy 진입 불가)
           warning만 → pass
           (03 게이트 로직 재사용: review_node node_status 산정 + WARN pass-through)
```

- 비전 AI = **Gemini**(기존 이미징 스택 일관). export(png/mp4)의 시각적 위반(이미지 내 텍스트·부적절 비주얼)을 metadata.md 콘티와 대조 검수.

## ② Iteration 루프 (명세 6)

`report.md` 권장 → 사용자가 **DesignStudio에서 수정**(ReviewStudio는 수정 안 함) → 확정 → ReviewStudio **R1~R3 전체 재실행**. 수정이 새 문제를 유발할 수 있으므로 증분이 아닌 **full 재검토**. 재검토 시 이전 verdict를 교체(`review.py` 멱등 재구축 패턴 재사용)해 stale BLOCK이 살아남지 않음.

## ③ 수정 분리 (명세 5 — 03으로부터의 변경점)

- ReviewStudio = `revise/` **권장만** 기록. design 폴더를 수정하지 않음.
- 03의 자동 수정(`remediation.fix_block_assets`, `creative_reviser`)은 **ReviewStudio 책임에서 제거** → DesignStudio(또는 사용자 수동 액션)로 귀속(미결).

## ④ 하네스 6요소 (다른 하네스와 대칭)

| 요소 | 내용 |
|---|---|
| 시스템 프롬프트 | 3 페르소나(법률 검토관 A · 동등성 검토관 B · 통합 reconciler C) |
| 제약/토큰 | 공식 법령 문서만(서칭 화이트리스트) · severity 규칙(critical=BLOCK / warning=pass) |
| 레퍼런스 | 서칭된 공식 법률 + `metadata.md` + 필수고지 마스터 |
| 구조화 출력 | `legal/` `i18n/` `revise/` `report.md` (포인팅 구조) |
| 크리틱/통합 | R3 reconciler(race 조정) |
| AskUser 훅 | iteration 확정 게이트(사용자 수정 → 확정) |
| (+) 공유 스킬 | 파일시스템 CRUD + **비전 AI 검수(Gemini)** |

## ⑤ 가상 폴더 (vfs.md `review/` 발췌)

```
/{runId}/review/
  legal/law_xxxx/    # R1: 위반 법률별 포인팅(조항·위치·근거)
  i18n/reason_xxx/   # R2: 동등성 사유별
  revise/{image,video}/  # R3: 최종 권장(수정 지시)
  report.md          # 종합 + 게이트 결과(critical/warning)
```

## 미결 / 후속 결정 항목

- 공식 법령 **서칭 소스** 구체화(법령 DB·화이트리스트).
- 자동 수정 로직 **귀속처**(DesignStudio reviser로 이동 여부).
- AskUser **bypass 세부**: critical은 BLOCK 강제(bypass 불가) / warning은 사용자 확정 후 진행.
- verdict **severity 스키마**(critical/warning 판정 기준) — 법률·동등성 공통.
