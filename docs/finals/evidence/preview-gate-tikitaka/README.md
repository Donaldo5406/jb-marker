# 시안 프리뷰 게이트 티키타카 검증 (2026-07-03, Mock·비용 0)

Plan 3(f85ed28..4b318e6) 배선을 게이트 전부 ON(바이패스 없음) 상태로 턴 단위 실측.
드라이버 `tikitaka.py`(로컬 uvicorn 8151, `DIRECTED_FULLBAKE=1`, mock=true, run 8993336ec359).

## 검증된 루프

| 턴 | 동작 | 결과 |
|---|---|---|
| 1 | 디자인 시작 | S0→**S1 게이트 정지**(confirm 봉투·critic 4.14). `rough/preview.html` 생성 — 팔레트 칩·factsheet 금리카드 6항목·존 레이아웃(4:5) 렌더 (`tk_shot_s1.png`) |
| 2 | 게이트 내 챗 교정 | S1 재실행 + preview 재기록 확인. **Mock 한계: 결정론 provider라 내용 불변** — 교정 반영 검증은 실 LLM 필요 |
| 3 | advance | **S2b 게이트**: 카피가 프리뷰에 반영(3.9→4.0KB). **그라운딩 critic 실동작**: mock 카피의 factsheet 밖 수치(4.0%·12개월·3.5%)를 적발(passed:false) → 인간 confirm으로 통과(실운영에선 챗 교정 대상) |
| 4 | advance | **S2a 게이트**: mock 베이크 비주얼이 프리뷰 캔버스 배경으로 base64 인라인(28KB, `tk_shot_final.png`) |
| 5 | advance | S2c — 프리뷰 불변(설계대로 4개 지점만 갱신) |
| 6 | advance | S3 통과 → **done**(리뷰 이동 안내). 최종 mock 포스터 `tk_final.png`(1.4MB) |

## 발견 (정직 고지)

- 🔴 **크레딧 소진(본선 D-1 최우선 블로커)**: 실 API 티키타카 시도에서 **Anthropic
  (credit balance too low) + Google 키 2개 전부(prepayment credits depleted, FinAI/.env·
  backend/.env 모두)** 실측 확인. 오늘 POC 5장(gemini-3-pro-image 2K)이 소진 가담 추정.
  충전 전까지 실 생성·본선 라이브 데모 전부 불가.
- Mock 티키타카의 한계: 챗 교정이 산출 내용에 반영되는지는 실 LLM에서만 검증 가능
  (스텝 재실행·프리뷰 재기록 메커니즘 자체는 검증됨).
- cosmetic: 프리뷰 캔버스에서 mock 비주얼이 중앙 영역만 채움(background-size 계열) —
  실 4:5 비주얼로 재확인 필요.
- 콕핏 UI(LayoutPreview iframe)는 이번엔 미검증 — 프리뷰 HTML을 브라우저 직접 렌더로
  대체(iframe srcdoc과 동일 콘텐츠). 프론트 실브라우저 검증은 실 API 검증과 함께 권장.
