# JB Marker

> **금융 마케팅 홍보물의 기획 → 디자인 → 준법 검토 → 발송을 하나의 파이프라인으로 잇는 멀티 기능 에디터 플랫폼.**
> 수동 편집과 AI 에이전트 편집을 한 화면에서 오가며, 모든 산출물은 근거(grounding)와 함께 기록된다.

JB금융그룹 Fin:AI Challenge **지정주제 3 — 디지털 마케팅 AI Agent** 출품작. `mvp/03-marketing`을 리팩토링하여 새 독립 레포로 재출발했다.
> 마케팅 콘텐츠의 **준법 사전심의**(지정주제 2의 문제의식)를 파이프라인에 내장해, 'AI 대량 생성'과 '건별 사람 심의'의 구조적 충돌을 정면으로 해소한다.

> 🆕 **2026-06-15 갱신** — **영상 제작(VideoStudio)** 파이프라인 추가 · 가운데 **"제작" 슬롯이 매체에 따라 Design↔Video로 스왑** · 이미지 **원-레이어 대전환**(`gemini-3-pro-image` 풀베이크). 본 README는 이 변경을 반영하며, 신규/변경 지점은 **🆕(신규)·🔄(변경)**로 표기한다.

---

## 라이브

- **웹앱**: https://jb-marker.vercel.app
- **백엔드 API**: https://doss-8b-instruct-jb-marker.hf.space (`/health` → `{"status":"ok"}`)
- **영속**: Supabase(Postgres · Auth · Storage) · `main` push 시 GitHub Actions가 Vercel·HF Space로 자동 배포

## 한눈에 보기

```
랜딩  →  콕핏(Workspace · History · Setting)  →  4-Studio 파이프라인 (가운데 "제작" 슬롯 = 매체 스왑) 🔄
                                                 ┌──────────────┬──────────────────┬────────────┬───────────┐
                                                 │ BrainStorming │ 제작: Design│Video│   Review   │  Deploy   │
                                                 │ 기획·매체택일 │   이미지/영상    │  준법심의  │  발송계획 │
                                                 └──────────────┴──────────────────┴────────────┴───────────┘
```

- **콕핏**: 작업의 허브. Workspace에서 `Use Marker`로 파이프라인을 시작하면 각 Studio가 탭으로 열리고, 상단 프로세스 바가 진행 단계를 추적·네비게이트한다.
- **Marker**: Claude 기반에 금융 마케팅 기획 하네스를 씌운 모델. BrainStorming·Design·**Video**·Deploy에서 역할별로 동작한다. 🔄
- **VFS(가상 폴더 트리)**: 모든 단계의 산출물이 저장되는 단일 소스. AI 산출은 항상 VFS를 경유해 grounding·메타데이터·History가 자동으로 붙는다.

## 스튜디오별 핵심

| 스튜디오 | 하는 일 | 핵심 |
| --- | --- | --- |
| **BrainStorming** 🔄 | 리서치 → 스펙(1단계) → 구현계획(2단계) 생성 · **매체(이미지/영상) 택일** | 가상 폴더 트리 · 모델 선택(Marker/Claude/GPT/Gemini) · AskUser 훅(WebSocket 중간 의사결정 UI) · **챗 헤더 매체 토글** |
| **Design**(이미지) 🔄 | 구현계획 기반: rough → 카피 → **원-레이어 풀베이크** → 고지/로고 오버레이 → 크리틱 | `gemini-3-pro-image`가 히어로 텍스트까지 베이크(광고급) · **필수고지·로고만 결정론 오버레이로 핀** · 다국어=언어별 베이크 재생성 · 에디터 보정 |
| **Video**(영상) 🆕 | 구현계획 기반: storyboard → Veo footage → 카피·고지 → 확정 렌더 | V0~V3 하네스 · VideoEditor(프리뷰·타임라인·고지 미터) · **고지 노출 ≥3초 게이트** · 확정 시 백엔드 **ffmpeg 렌더** → `review/_render/final.mp4` |
| **Review** | 준법 검토 + 다국어 동등성 검토 | 실제 법령 기반 위반 포인팅 · 비전 AI 검수 · % 게이지 진행 표시 · 수정은 사용자 위임 후 재검토 (mvp/02 확장판) |
| **Deploy** | 발송 행위의 적법성 판정 + 발송 계획 | 결정론 규칙엔진(정보통신망법 §50 동의·야간·옵트아웃 + 개인정보보호법 §15 목적·§16 보유기간) · 다중 정책(가장 강한 BLOCK 채택) · 발송 어댑터 stub · D2 카피 적응 advisor |

> 🔄 **제작 슬롯**: Design(이미지)과 Video(영상)는 매체 택일로 결정되는 가운데 "제작" 슬롯의 두 얼굴이다(한 런=한 매체). Review/Deploy는 매체와 무관하게 동일하게 잇는다.
> Review는 **콘텐츠의 적법성**, Deploy는 **발송 행위의 적법성**을 다룬다. Deploy의 실제 발송은 stub/시뮬이며 실 dispatch는 범위 밖이다.

## 설계 원칙

- **SSOT = 이 레포의 코드 + `docs/`.** 외부(01·02 주제 코드/문서)와 메모리는 비참조.
- **상태의 유일한 주인 = 저장소** (로컬 우선 → Supabase). LangGraph 미사용.
- **AI 산출은 항상 VFS 경유 서빙** — grounding·메타·History 자동 부착.
- **로컬 우선** — 키가 없어도 부팅되며, 프로바이더 키가 있으면 실 LLM으로 승격된다.

## 디렉터리 구조

```
jb-marker/
├── frontend/                  # Next.js(App Router) + TS + Tailwind + motion + fabric v7 → Vercel
│   ├── app/                   # 라우트: page(랜딩) · cockpit · pricing · showcase
│   └── components/            # cockpit(+deploy · VideoStudio · editor/VideoEditor) · landing · ui  🔄
├── backend/                   # FastAPI + Python(>=3.11) → HF Space (ffmpeg + 한글 폰트 번들) 🆕
│   └── app/
│       ├── gateway/           # Marker API 게이트웨이 + 하네스 + entitlement
│       │   ├── pipeline.py    #   공용 PipelineOrchestrator (design·video 공유) 🆕
│       │   ├── design/        #   이미지 단계(steps·prompts·scoring) — 원-레이어 풀베이크 🔄
│       │   └── video/         #   영상 단계(steps·prompts·scoring·render ffmpeg) 🆕
│       ├── vfs/               # 가상 폴더 트리 SSOT (local · supabase · factory)
│       ├── deploy/            # 규칙엔진·eligibility·ledger·packager·providers + policies/{infomatics,pipa}.yaml
│       ├── observability/     # run별 토큰·비용 트래킹(usage) + 단가표(pricing)
│       ├── providers/         # anthropic·openai·google(generate_image·generate_video)·fake + registry  🔄
│       ├── core/              # grounding · legal_search · severity
│       ├── references/        # legal/whitelist.json · design/*.json(few-shot 자산)
│       └── assets/music/      # 영상 렌더 음악 베드(CC0) 🆕
└── docs/                      # 자체완결 SSOT
    ├── Refactor.md            # 기획 SSOT (배경·아키텍처·운영 결정 C1~C4·DoD·Non-goals)
    ├── design/                # 설계 문서: DESIGN·LANDING·NAVIAGTE·*_subharness·vfs·marker_api 등
    ├── specs/                 # 마일스톤별 설계(spec)
    └── plans/                 # 마일스톤별 구현계획(plan)  — brainstorming → writing-plans 산출물
```

## 빌드 마일스톤 (전 단계 완료 · 라이브 배포)

| # | 마일스톤 | 상태 |
|---|---|---|
| M0 | 레포 스캐폴드 & 디자인 시스템 | ✅ 완료 |
| M1 | VfsStore + Marker API 게이트웨이 | ✅ 완료 |
| M2 | 프론트 셸: 랜딩 + 콕핏 + 네비게이션 (E2E) | ✅ 완료 (PR #1) |
| M3 | BrainStormingStudio | ✅ 완료 (PR #2) |
| M4 | DesignStudio (S0~S3 파이프라인 · 3액터 · Fabric.js v7 에디터) | ✅ 완료 |
| M5 | ReviewStudio (준법 + 다국어 동등성) | ✅ 완료 (PR #3) |
| M6 | DeployStudio (§50+§15·§16 결정론 규칙엔진 · advisor · 토큰/비용 관측) | ✅ 완료 (PR #5·#6·#7) |
| M7-A | Supabase 영속 + 실 Auth(익명 JWT · 소유권 가드 · RLS) | ✅ 완료 |
| M7-B | History 갤러리(목록→상세 · 디자인시스템 iframe 프리뷰) | ✅ 완료 |
| M7-C | 실배포 (Vercel · HF Space · Supabase 라이브) | ✅ 완료 |
| O1~O4 | 횡단 정책(세션 수명주기 · Design confirm 게이트 · 안정 이벤트 · 긴 스레드 compaction) | ✅ 완료 |
| T3 🔄 | 하네스 모듈화(공용 `PipelineOrchestrator`) + **이미지 원-레이어 대전환**(`gemini-3-pro-image` 풀베이크) | ✅ 완료 (PR #71) |
| T2 🔄 | 프론트 UX 정합(게이트 봉투 `gate.actions` 동적 소비 · 세션 수명주기 UI · 타입 SSOT) | ✅ 완료 (PR #70·#72) |
| V (P1~P5) 🆕 | **VideoStudio** — Veo 시네마틱 생성 · ffmpeg 서버 렌더 · VideoEditor · 매체 토글·nav 슬롯 스왑 · demo medium=video e2e | ✅ 완료·라이브 (PR #74~#88) |

> **테스트**: 백엔드 `pytest` / 프런트 `vitest`, CI green — **영상 파이프라인 V0~V3 + render Mock e2e 회귀 잠금 포함** 🆕. *(환경에 따라 ±, 제출 직전 클린 `.env` 격리 측정으로 확정 권장)*

## 로컬 실행

**백엔드** (FastAPI · `localhost:8000`)

```bash
cd backend
pip install -e ".[dev]"      # 실 LLM 라이브 검증 시: pip install -e ".[dev,live]"
cp .env.example .env         # 키 없어도 부팅됨
uvicorn app.server:app --reload
```

**프런트** (Next.js · `localhost:3000`)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

**테스트 / 빌드**

```bash
cd backend  && pytest
cd frontend && npm run test && npm run typecheck && npm run build
```

## 환경변수

각 디렉터리의 `.env.example`를 복사해 사용한다 (로컬 우선 — 키 없어도 부팅).

| 변수 | 위치 | 용도 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | backend | Marker(Claude) 하네스 · Review · Deploy advisor 실 LLM |
| `GOOGLE_API_KEY` | backend | 텍스트 Gemini + **이미지(`gemini-3-pro-image`) + 영상 footage(Veo)** 공용 🔄 |
| `GOOGLE_IMAGE_MODEL` | backend | 이미지 모델 오버라이드(기본 `gemini-3-pro-image` — 비용 절감 시 flash 계열로 교체) 🆕 |
| `OPENAI_API_KEY` | backend | GPT 모델 선택지 |
| `VFS_BACKEND` | backend | `local` \| `supabase`(운영 기본, M7 라이브) 🔄 |
| `ENTITLEMENT_OVERRIDE` | backend | `1`이면 데모용 유료 게이트 우회 (실 PG 청구는 Non-goal) |
| `ADVISOR_MODE` | backend | `auto`(키 있으면 live, 없으면 scripted) \| `live` \| `scripted` |
| `NEXT_PUBLIC_API_BASE` | frontend | 백엔드 주소 (기본 `http://localhost:8000`) |

모델은 미지정 시 기본값 사용: `claude-sonnet-4-6` · `gpt-4o` · `gemini-2.0-flash`(텍스트) · **`gemini-3-pro-image`(이미지)** 🔄 · **`veo-3.0-generate-001`(영상)** 🆕.
영상 최종 mp4 렌더는 백엔드 호스트의 **ffmpeg 바이너리 + 한글 폰트**가 필요하다(부재 시 still 폴백). 🆕

> **Mock(데모) 모드** 🔄: 콕핏 Setting의 토글 ON → 전 스튜디오가 무료·결정적 더미 응답(`DemoProvider`)으로 **끝까지 완주**한다(정기예금 4언어 fixture·placeholder 비주얼). BrainStorming→제작(Design \| Video)→Review→Deploy가 실 LLM 호출·과금 없이 진행돼 시연 영상에 적합. **매체=영상 선택 시 storyboard→footage→렌더 폴백 mp4까지 키·ffmpeg 없이 완주**(demo footage는 실 Veo 광고영상 b64 임베드). 요청 단위 플래그(상태 비영속·라이브 안전). 실제 산출물 제작 시 OFF + 프로바이더 키 설정.

## 스택

- **프런트**: Next.js (App Router) · TypeScript · Tailwind · motion · Fabric.js v7 · lucide-react · vitest
- **백엔드**: FastAPI · uvicorn · websockets · httpx · pyyaml · (선택) anthropic / openai / google-genai · **ffmpeg(영상 렌더 시스템 바이너리)** 🆕 · pytest

## 보안 — 알려진 npm audit 예외

`#10`에서 실질 런타임 위험을 우선 제거했다: **fabric 6→7**(SVG export XSS, PR #29) · **next 14.2.35 패치**(authorization bypass·content injection·일부 cache poisoning, PR #30).

남은 `npm audit` 항목(2026-06 기준 10건)은 아래 사유로 의도적으로 보류한다. 대부분 프로덕션 번들에 포함되지 않거나, 본 앱이 쓰지 않는 조건부 기능에 한정된다.

| 항목 | 심각도 | 보류 사유 |
| --- | --- | --- |
| `next` 잔여 | high·critical | 주로 DoS + 자체호스팅 image optimizer·Pages Router i18n·WebSocket 등 **조건부**. 완전 해소는 next 16 메이저(async request API·React 19 동반)가 필요해 별도 평가 대상. 본 앱은 App Router·Vercel 배포라 실노출이 제한적. |
| `glob` · `eslint-config-next` · `minimatch` | high | **dev 전용**(lint CLI). 프로덕션 번들과 무관. `eslint-config-next` 16(next 16 동반) 필요. |
| `esbuild` · `vite` · `vitest` | moderate | **dev 전용**(테스트 개발 서버). 프로덕션과 무관. vitest 4 전환은 vite 8(oxc)·plugin-react·TypeScript 연쇄 비용이 효과를 초과해 보류. |
| `postcss` | moderate | next 경유. next 16에서 해소. |

재평가 트리거: next 16 메이저를 진행하면 위 항목 대부분이 함께 해소된다.
