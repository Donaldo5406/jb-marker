# 레이어 추출 — JB 20대 청년 정기예금 (run `d07bd88265f9`)

우리 파이프라인이 실제로 저장하는 **개별 파일**들입니다. GPT는 레이어를 그린 **그림 1장**을 주지만,
아래는 각각 **열어서 편집 가능한 실제 파일**입니다.

| 파일 | 크기 | mime | 성격 |
|---|---|---|---|
| `_material_matrix.json` | 64B | application/json | ⚙️ 파이프라인 상태/구성 |
| `_session.json` | 246B | application/json | ⚙️ 파이프라인 상태/구성 |
| `_state.json` | 230B | application/json | ⚙️ 파이프라인 상태/구성 |
| `design-system/components/body/en.txt` | 65B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/body/ko.txt` | 66B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/cta/en.txt` | 16B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/cta/ko.txt` | 26B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/disclosure/ko.txt` | 171B | text/plain | ✅ 실제 편집 레이어 — 법정 고지(벡터 텍스트 오버레이) |
| `design-system/components/headline/en.txt` | 31B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/headline/ko.txt` | 45B | text/plain | 📄 카피 데이터(.txt) — 현재는 히어로에 베이크됨(별도 시각 레이어 아님) |
| `design-system/components/logo/ko.txt` | 6B | text/plain | · |
| `design-system/components/logo/v1.png` | 17,994B | image/png | ✅ 실제 편집 레이어 — 로고(결정론 오버레이 PNG) |
| `design-system/components/visual/v1.png` | 642,682B | image/png | 🖼️ 베이크 히어로(사진+헤드라인/바디/CTA가 여기 구워짐) |
| `design-system/tokens.json` | 312B | application/json | ⚙️ 파이프라인 상태/구성 |
| `metadata.md` | 769B | text/markdown | 📄 메타(카피·크리틱 점수 요약) |
| `rough/layout.spec.json` | 2,780B | application/json | 🧩 씬 그래프 — slots/bbox/color/copy (편집기가 읽는 레이어 정의) |

## 요약
- 🖼️ **베이크 히어로 1장**: 인물사진 + 헤드라인/바디/CTA가 여기 함께 구워짐(현재 구조).
- ✅ **실제 편집 레이어**: 로고(PNG 오버레이), 고지(벡터 텍스트) — 히어로와 분리돼 개별 편집됨.
- 🧩 **씬 그래프(layout.spec.json)**: slots(role·bbox·color·font_px)로 레이어 배치를 정의 — 편집기가 이걸 읽어 레이어를 그림.
- 📄 **카피 .txt**: 헤드라인/바디/CTA는 지금은 '데이터'로만 저장되고 시각은 히어로에 베이크 → **단조로움의 원인은 여기**(별도 시각 레이어·위젯이 없음).

## 결론
'다 텍스트로 저장해서 단조롭다'기보다, **텍스트가 사진에 베이크되고 금리카드·혜택행 같은 벡터 크롬 레이어가 없어서** 단조롭다.
명세(2026-07-02-rich-editable-vector-layers)의 방향 = 이 카피들을 **벡터/이미지 레이어로 승격 + 금리카드·혜택행 추가**.