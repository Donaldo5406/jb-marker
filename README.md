# JB Marker

> **금융 마케팅 홍보물의 기획 → 디자인 → 준법 검토 → 발송을 하나의 파이프라인으로 잇는 멀티 기능 에디터 플랫폼.**
> 수동 편집과 AI 에이전트 편집을 한 화면에서 오가며, 모든 산출물은 근거(grounding)와 함께 기록된다.

JB금융그룹 Fin:AI Challenge 자유주제 출품작. `mvp/03-marketing`을 리팩토링하여 새 독립 레포로 재출발했다.

---

## 한눈에 보기

```
랜딩  →  콕핏(Workspace · History · Setting)  →  4-Studio 파이프라인
                                                 ┌──────────────┬───────────┬────────────┬───────────┐
                                                 │ BrainStorming │  Design   │   Review   │  Deploy   │
                                                 │  기획·스펙    │  디자인   │  준법심의  │  발송계획 │
                                                 └──────────────┴───────────┴────────────┴───────────┘
```

- **콕핏**: 작업의 허브. Workspace에서 `Use Marker`로 파이프라인을 시작하면 각 Studio가 탭으로 열리고, 상단 프로세스 바가 진행 단계를 추적·네비게이트한다.
- **Marker**: Claude 기반에 금융 마케팅 기획 하네스를 씌운 모델. BrainStorming·Design·Deploy에서 역할별로 동작한다.
- **VFS(가상 폴더 트리)**: 모든 단계의 산출물이 저장되는 단일 소스. AI 산출은 항상 VFS를 경유해 grounding·메타데이터·History가 자동으로 붙는다.

## 스튜디오별 핵심

| 스튜디오 | 하는 일 | 핵심 |
| --- | --- | --- |
| **BrainStorming** | 리서치 → 스펙(1단계) → 구현계획(2단계) 생성 | 가상 폴더 트리 · 모델 선택(Marker/Claude/GPT/Gemini) · AskUser 훅(WebSocket으로 중간 의사결정 선택 UI) |
| **Design** | 구현계획 기반 디자인: rough → 컴포넌트 단계 → final confirm | 대형 Fabric.js v6 에디터 + AI 챗 패널 · 3액터(Marker·Gemini/Nano Banana·Fabric.js) · 다국어 버전 산출 · Review용 메타데이터 저장 |
| **Review** | 준법 검토 + 다국어 동등성 검토 | 실제 법령 기반 위반 포인팅 · 비전 AI 검수 · % 게이지 진행 표시 · 수정은 사용자 위임 후 재검토 (mvp/02 확장판) |
| **Deploy** | 발송 행위의 적법성 판정 + 발송 계획 | 결정론 규칙엔진(정보통신망법 §50 동의·야간·옵트아웃 + 개인정보보호법 §15 목적·§16 보유기간) · 다중 정책(가장 강한 BLOCK 채택) · 발송 어댑터 stub · D2 카피 적응 advisor |

> Review는 **콘텐츠의 적법성**, Deploy는 **발송 행위의 적법성**을 다룬다. Deploy의 실제 발송은 stub/시뮬이며 실 dispatch는 범위 밖이다.

## 설계 원칙

- **SSOT = 이 레포의 코드 + `docs/`.** 외부(01·02 주제 코드/문서)와 메모리는 비참조.
- **상태의 유일한 주인 = 저장소** (로컬 우선 → Supabase). LangGraph 미사용.
- **AI 산출은 항상 VFS 경유 서빙** — grounding·메타·History 자동 부착.
- **로컬 우선** — 키가 없어도 부팅되며, 프로바이더 키가 있으면 실 LLM으로 승격된다.

## 디렉터리 구조

```
jb-marker/
├── frontend/                  # Next.js(App Router) + TS + Tailwind + motion + fabric v6 → Vercel
│   ├── app/                   # 라우트: page(랜딩) · cockpit · pricing · showcase
│   └── components/            # cockpit(+deploy) · landing · ui
├── backend/                   # FastAPI + Python(>=3.11) → HF Space
│   └── app/
│       ├── gateway/           # Marker API 게이트웨이 + 하네스(brainstorming·design·review·advisor) + entitlement
│       ├── vfs/               # 가상 폴더 트리 SSOT (local · supabase · factory)
│       ├── deploy/            # 규칙엔진·eligibility·ledger·packager·providers + policies/{infomatics,pipa}.yaml
│       ├── observability/     # run별 토큰·비용 트래킹(usage) + 단가표(pricing)
│       ├── providers/         # anthropic·openai·google·fake 클라이언트 + registry(모델 교차 이용)
│       ├── core/              # grounding · legal_search · severity
│       └── references/        # legal/whitelist.json · design/*.json(few-shot 자산)
└── docs/                      # 자체완결 SSOT
    ├── Refactor.md            # 기획 SSOT (배경·아키텍처·운영 결정 C1~C4·DoD·Non-goals)
    ├── design/                # 설계 문서: DESIGN·LANDING·NAVIAGTE·*_subharness·vfs·marker_api 등
    ├── specs/                 # 마일스톤별 설계(spec)
    └── plans/                 # 마일스톤별 구현계획(plan)  — brainstorming → writing-plans 산출물
```

## 빌드 마일스톤 (전체 8단계 중 7단계 완료)

| # | 마일스톤 | 상태 |
|---|---|---|
| M0 | 레포 스캐폴드 & 디자인 시스템 | ✅ 완료 |
| M1 | VfsStore + Marker API 게이트웨이 | ✅ 완료 |
| M2 | 프론트 셸: 랜딩 + 콕핏 + 네비게이션 (E2E) | ✅ 완료 (PR #1) |
| M3 | BrainStormingStudio | ✅ 완료 (PR #2) |
| M4 | DesignStudio (S0~S3 파이프라인 · 3액터 · Fabric.js v6 에디터) | ✅ 완료 |
| M5 | ReviewStudio (준법 + 다국어 동등성) | ✅ 완료 (PR #3) |
| M6 | DeployStudio (§50+§15·§16 결정론 규칙엔진 · advisor · 토큰/비용 관측) | ✅ 완료 (PR #5·#6·#7) |
| M7 | History + 통합·배포 (Supabase · 실 Auth · 실배포) | ⏳ 대기 (마지막) |

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
| `GOOGLE_API_KEY` | backend | 텍스트 Gemini + Nano Banana(M4 이미지 생성) 공용 |
| `OPENAI_API_KEY` | backend | GPT 모델 선택지 |
| `VFS_BACKEND` | backend | `local` \| `supabase`(M7 예정) |
| `ENTITLEMENT_OVERRIDE` | backend | `1`이면 데모용 유료 게이트 우회 (실 PG 청구는 Non-goal) |
| `ADVISOR_MODE` | backend | `auto`(키 있으면 live, 없으면 scripted) \| `live` \| `scripted` |
| `NEXT_PUBLIC_API_BASE` | frontend | 백엔드 주소 (기본 `http://localhost:8000`) |

모델은 미지정 시 기본값 사용: `claude-sonnet-4-6` · `gpt-4o` · `gemini-2.0-flash`.

> **Mock(데모) 모드**: 콕핏 Setting의 토글 ON → 전 스튜디오(텍스트·이미지·비전·advisor)가 무료·결정적 더미 응답(FakeProvider)으로 동작(시연 영상용, 요청 단위·라이브 안전). 실제 산출물 제작 시 OFF + 프로바이더 키 설정.

## 스택

- **프런트**: Next.js (App Router) · TypeScript · Tailwind · motion · Fabric.js v7 · lucide-react · vitest
- **백엔드**: FastAPI · uvicorn · websockets · httpx · pyyaml · (선택) anthropic / openai / google-genai · pytest

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
