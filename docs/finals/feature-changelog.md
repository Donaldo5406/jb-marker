# 본선 기능 변경 기록 (CUD Changelog)

> 본선(2026-07-04~05) 중 **새 사용자 기능·화면·엔드포인트·옵션**을 추가/변경/삭제하면 여기에 즉시 기록한다.
> 기능명세 제출 대상 판별의 단일 근거. **순수 최적화(품질·폴리시·프롬프트·렌더 개선)는 기록하지 않는다**(→ `optimization-report.md`).

| 일시 | 구분(C/U/D) | 무엇 | 왜 | 사용자 가시 변화 | 커밋 |
| --- | --- | --- | --- | --- | --- |
| 2026-07-04 | D | 결제 표면 전면 폐기 — `/pricing` 페이지·랜딩 "결제" 메뉴·데모 결제 모달·`POST /deploy/demo-payment`·`_state.dev_pass` | 제품 목적(은행 내부 준법 마케팅 코파일럿)에 소비자 결제 서사 불일치 (사용자 지시) | 랜딩에서 결제 메뉴 사라짐, Deploy 발송 확정이 결제 모달 없이 바로 진행(권한 오류는 에러 텍스트). 엔타이틀먼트 토글(Setting)은 유지 | a53a788, 1a4e9bd |
| 2026-07-04 | C | Mock 자연 레이턴시 `DEMO_LATENCY_MS`(env, 기본 0=끔) | mock 즉답이 라이브 데모에서 인위적으로 보임 | 데모 서버에서 AI 답변·베이크가 응답 길이 비례(상한 2.5~3s)의 자연스러운 대기 후 표시 | a53a788 |
| 2026-07-04 | U | 교정(revise) 재베이크를 image-edit(img2img)로 전환 + 비ko 언어 변형 fixture 3장 | 재생성마다 포스터가 통째로 바뀌어 "카피만 교정" 서사가 약함 · vi/en/zh가 PIL 폴백이라 ko와 품질 격차 | 검토 후 교정 시 기존 포스터 아트를 유지한 채 텍스트만 교체됨, 언어 전환 시 en/vi/zh도 ko와 동급 골드 캘리 포스터 | d69f899, (this) |
| 2026-07-04 | C | JB 브랜드 지식 팩 신규 — `backend/app/references/brand/jb_group.yaml`(공식 CI 컨셉 PEOPLE·JB DIAMOND·SPACE·슬로건·실측 팔레트·로고 규정; 신뢰등급·출처 병기, as_of 스탬프. **products 섹션은 프롬프트 주입 금지**) + `backend/app/gateway/design/brand_context.py`(저변동 계층만 4~6줄 렌더, 부재 시 None 강하) | 생성 소재 기본 톤을 JB CI에 수렴시키되 시의성(상품·금리)은 팩에서 분리 — 시의성 SSOT는 런타임 | 없음(내부; 지시 없을 때만 생성 소재 기본 톤이 JB CI로 수렴) | 94f5863 |
| 2026-07-04 | U | Design S1 프롬프트 레퍼런스 말미에 브랜드 블록 append(사용자 지시·tokens 우선 명시) + History(RunList) 데모 표시 제목 3건을 현행 실상품으로(표시 전용) | 지시 없을 때만 JB CI 톤으로 수렴시키되 사용자 지시가 항상 우선 · 데모 표시 제목이 현행 실상품과 불일치 | 없음(지시 없을 때 기본 톤만 수렴) · History 목록의 데모 제목이 현행 실상품명으로 표시 | 92fc483, 122d37e |
| 2026-07-04 | C | "동작 원리" 아키텍처 소개 페이지 신설 — `/architecture`(시스템 흐름 8단계 자동 루프 다이어그램 · AI 에이전트 루프+4종 하네스 · 기술 스택 표) + 랜딩 네비 "동작 원리" 항목 | 심사 대응: 풀스택 구조·Agent 활용 방식을 비개발자도 이해하도록 제품 안에서 직접 설명 | 랜딩 상단 메뉴에 "동작 원리" 추가, 클릭 시 애니메이션 아키텍처 페이지(#flow·#agent·#stack) | (this) |
| 2026-07-04 | C | 스튜디오별 파일 업로드 소스화 — FileTree 업로드 버튼(Brain·Design·Review에서 노출) | Brain/Design/Review 각 스튜디오가 AI 소비 데이터(spec/plan·카피·심의 소재)를 자율 업로드 가능토록 제공 | 각 스튜디오의 FileTree에 업로드 버튼 추가, 업로드 파일은 `{studio}/uploads/`에 저장되어 AI 참조 · mock: 트리거 이미지 업로드 시 Review 결정론 적발(BLOCKED) 재현 가능 | (this) |
| 2026-07-04 | C | Review Studio 하이라이트 오버레이 — 신설 엔드포인트 `GET /runs/{id}/review-highlight`, verdict `location` 비파괴 확장(`bbox`/`image`), `HighlightFrame`(iframe srcDoc). Mock=정적 authored bbox(구절-tight)·Live=비전/OCR 소스 교체 구조 | 심의 결과가 텍스트 카드로만 설명돼 "이미지의 어디가 문제인지"를 시각적으로 못 짚음(시연 설득력·5.5 리스크 대응) | Review Studio 좌열 상단에 검토 포스터가 뜨고 위반 문구에 마커펜(치명=빨강/경고=노랑)+번호 핀이 그어져 근거 카드와 연결됨. 카드/시각 뷰 토글. bbox 없으면 기존 카드뷰로 축퇴 | (this) |
