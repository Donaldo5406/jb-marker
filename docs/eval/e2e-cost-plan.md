# D4 — 실기능 E2E 테스트 설계 · 비용 산정 · 마케팅물 제작 방법론

> 입력: D2 감사로 확인한 스튜디오별 LLM/이미지 호출 횟수 + 검증된 단가표(`observability/pricing.py`).
> 규모: **풀 시나리오**(다국어 × 다채널 매트릭스, 사용자 확정).
> 산출: 비용 모델 → **충전 권장액** → 실제 마케팅물 제작 절차.

## 1. 풀 시나리오 정의

| 축 | 값 | 근거 |
| --- | --- | --- |
| 캠페인 | 1종 (예: 정기예금/적금 홍보 — 포스터+배너) | 단위 산출 |
| 언어 | **4종**: ko(기준)·en·vi·zh | `severity.py`의 i18n 동등성 안전망이 vi/zh/en 지원 |
| 채널 | **6종**: email·kakao·sms·naver·google·instagram | `deploy/registry.py` 등록 채널 |

→ "1 풀세트 = 1 캠페인 × 4언어 × 6채널" 을 비용 산정 단위로 한다.

## 2. 스튜디오별 호출 횟수 (D2 감사 확인값)

| 스튜디오 | 텍스트 LLM | 이미지 | 비전 | 결정론(LLM 0) | 출처 |
| --- | --- | --- | --- | --- | --- |
| BrainStorming | ~4 (완주 최소 2 + 다듬기) | 0 | 0 | — | `harness_brainstorming.py:214,296` |
| Design | ~5 (S1생성+S1critic+S2b+S3critic×2) | 1 | 0 | S0 | `harness_design.py:258,279,300,366` |
| Review | 3 (R1+R2+R3, R1 web_search 최대 3라운드) | 0 | 1+N_lang(=5) | — | `harness_review.py:251,382,467` |
| Deploy | advisor ~8턴(채널×조정) | 0 | 0 | **rules·eligibility 전부** | `deploy/advisor/chat.py`, `rules_engine.py` |

- 모델: 텍스트=`claude-sonnet-4-6`, 이미지=`gemini-2.5-flash-image`, 비전=`gemini-2.5-flash` (서버 바인딩 `server.py:139-140,255,258`).
- max_tokens: 텍스트 8192, advisor 2048.

## 3. 단가 (검증됨 — `pricing.py:9-30`)

| 모델 | input ($/1M) | output ($/1M) | 비고 |
| --- | --- | --- | --- |
| claude-sonnet-4-6 | 3.00 | 15.00 | 텍스트 주력 |
| gemini-2.0-flash | 0.10 | 0.40 | (대체 텍스트) |
| gemini-2.5-flash-image | — | — | **$0.04 / 이미지** |
| gpt-4o | 2.50 | 10.00 | (선택) |
| Anthropic web_search | — | — | **$0.01 / search** (별도 과금) |

## 4. 비용 산정 (1 풀세트, USD)

토큰 추정 가정: 한글 1자 ≈ 1.5토큰. system+컨텍스트 인라인이 input 지배. 보수적 상향.

| 스튜디오 | 계산 | 소계 |
| --- | --- | --- |
| BrainStorming | 4 × [(7K in×$3 + 4K out×$15)/1M = $0.081] | **$0.32** |
| Design | 5 × [(6K×3 + 4K×15)/1M = $0.078] + 이미지 1×$0.04 + 재생성버퍼 $0.12 | **$0.55** |
| Review | R1 $0.144 + websearch 3×$0.01 + R2 $0.072 + R3 $0.075 + 비전 5회 ≈$0.00 | **$0.32** |
| Deploy | rules/eligibility $0 + advisor 8턴 × [(2.5K×3+1.5K×15)/1M=$0.03] | **$0.24** |
| **1 풀세트 합계** | | **≈ $1.43 (약 2,000원)** |

> 비전(gemini-2.5-flash) 5회는 이미지 입력 토큰이 작아 합산 $0.01 미만 — 사실상 무시 가능.
> 핵심 비용 동인은 **claude-sonnet-4-6의 output 토큰(8192 상한)**.

### 4.1 제출 준비 총비용 (반복·버퍼 포함)

| 항목 | 수량 | 비용 |
| --- | --- | --- |
| 제출용 실제 마케팅물 | 2~3 풀세트(캠페인 다양성) | $3 ~ $4.5 |
| 실패·재생성·다듬기·실험 버퍼 | ×3 | $9 ~ $13.5 |
| 시연영상 | Mock 모드(C1) | **$0 (무료)** |
| **제작 단계 총합** | | **≈ $12 ~ $18** |

## 5. 충전 권장액

| Provider | 용도 | 권장 | 최소 안전선 |
| --- | --- | --- | --- |
| **Anthropic** | 텍스트 LLM 전 스튜디오 + web_search | **$25** | $15 |
| **Google** | 이미지 생성 + 비전 검수 | **$10** | $7 |
| OpenAI (선택) | GPT 모델 비교용 | $5 | $0 |
| **합계** | | **≈ $40 (약 56,000원)** | **≈ $22 (약 31,000원)** |

> 환율 ~1,400원/USD 기준. **권장 $40이면 풀세트 약 20회 + 시연 보조까지 여유**. 최소 $22로도 5~8 풀세트 가능.
> 주의: ① Anthropic 결제 최소 단위(보통 $5)·web_search 별도 과금. ② **라이브 백엔드(HF Space)에 키를 넣으면 모든 사용자 호출이 과금** → 제작 시에만 Mock OFF, 평소 Mock ON 권장. ③ `usage` 대시보드(`/runs/{id}/usage`)로 실비용 모니터링.

## 6. E2E 테스트 설계

### 6.1 2단 전략

- **Stage 1 — Mock E2E (무료·결정적)**: C1 Mock 토글 ON. 전 파이프라인 구조·흐름·산출물 경로·게이트 동작·usage 0원 기록 검증. 시연 영상도 이 모드.
- **Stage 2 — Live E2E (유료·품질)**: 실 키. 풀세트 1회 완주로 산출물 **품질**·grounding·다국어 동등성·준법 판정 정확성 검증. 제출 첨부용 산출물 캡처.

### 6.2 단계별 검증 포인트

| 단계 | 검증 항목 | 합격 기준 |
| --- | --- | --- |
| BrainStorming | spec.md·plan.md 생성, plan frontmatter 9키 충족 | `critic` 누락 0(`harness_brainstorming.py:84-90`) |
| Design | layout.spec.json + 비주얼 PNG + 4언어 카피 | Live: PNG 실이미지(1x1 폴백 아님), grounding ungrounded 0 |
| Review | verdict.json + report.md, 4언어 동등성 | critical=0→PASS / WARN ack, live_unavailable 아님 |
| Deploy | eligibility 판정 + 발송계획 simulation.json | §50/§15/§16 결정론 판정 정확, 다중정책 BLOCK 우선순위 |

### 6.3 회귀 안전망

- Live E2E 전 `pytest`(클린 `.env` 격리) 338 통과 확인 → 코드 회귀 없음 보증.
- usage 로그(`/{run}/usage/log.jsonl`)로 호출 횟수가 §2 예측과 일치하는지 대조(비용 폭주 조기 탐지).

## 7. 실제 마케팅물 제작 절차 (Live)

1. **키 설정**: 백엔드 `.env`(로컬) 또는 HF Space secrets에 `ANTHROPIC_API_KEY`·`GOOGLE_API_KEY` 설정. `ENTITLEMENT_OVERRIDE` 의도 확인.
2. **Mock OFF**: 프론트 Setting에서 Mock 모드 OFF(C1).
3. **캠페인 입력**: 상품·타깃·언어(4)·채널(6) 지정 → `Use Marker`로 파이프라인 시작.
4. **BrainStorming**: 기획 문답 → spec 확정 → plan 확정(confirm 게이트).
5. **Design**: rough→비주얼→카피(4언어)→브랜드→final. 게이트마다 검수.
6. **Review**: 준법 + 다국어 동등성 검토. WARN이면 수정 위임 후 재검토, ack.
7. **Deploy**: 적격성 판정 → 발송계획(채널별, **시뮬**) → advisor로 D2 카피 적응.
8. **산출물 수집**: VFS 트리에서 최종 PNG·카피·리포트 export. usage 대시보드로 실비용 확인.
9. **검수·정정**: D3 critique 반영 — overclaim 없는지, 수치 grounding 충족했는지 최종 확인.

## 8. 리스크·주의

- **비용 폭주**: 라이브에 키 상주 시 외부 사용자 호출도 과금. 제작 세션 외 Mock ON 유지 권장.
- **이미지 폴백 함정**: 키 누락 시 1x1 PNG가 "생성 완료"로 표시(`harness_design.py:278-286`). Live 산출물은 PNG 실측 필수.
- **Review fail-open**: 키 장애 시 WARN까지만(`severity.py:79-82`). 제출 산출물은 live_unavailable=false 확인.
- **dispatch는 시뮬**: 실제 발송 아님(`stub.py`). 마케팅물은 "제작·검토 완료"까지, 발송은 Non-goal.
