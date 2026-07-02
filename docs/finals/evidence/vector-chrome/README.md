# 히어로 우선 벡터 크롬 — 라이브 스모크 증빙 (2026-07-03)

`RICH_VECTOR_CHROME=1` 실 API 스모크(run 357937e5c833, 청년 정기예금, gemini-3-pro-image).

- `hero_textfree_cheongnyeon.png` — S2a rich 경로가 생성한 **텍스트 프리 히어로**.
  글자 0(폰 화면 블랭크·간판 보케)·광고급 시네마틱·하단 솔리드 푸터 밴드(고지 세이프존)·
  텍스트 레이어용 네거티브 스페이스. 텍스트누출 vision 게이트 통과.
- layout.spec.json 실측: `render_mode=vector_chrome`, roles 8종
  (background·headline·body·rate_card·benefit_row·cta_button·disclosure·logo 전부),
  헤드라인 폰트=GmarketSansBold 800(무드 youth 자동선택), 잉크색 #183474(**히어로에서
  vision이 추출한 팔레트**), 금리카드 lines·혜택행 items 전부 factsheet 그라운딩
  (최고 연 3.30% · 연 2.80% · 우대 0.50%p · 6~36개월 · 100만원), 환각 0.

전 마케팅 텍스트(헤드라인·금리카드·혜택행·CTA·고지)는 프론트 편집 벡터 레이어로 렌더됨
(Plan 1). 재현: RICH_VECTOR_CHROME=1 로컬 uvicorn → scratchpad/drive_rich.py.
