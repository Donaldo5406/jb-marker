mvp 03 리팩토링 계획을 세웁니다. 이것은 새로 git init 될 예정이고, 레포지토리 이름은 JB marker 입니다. \
아래 상세한 기획서를 읽고, 필요한 질문을 나에게 합니다. 

    [배경]
    - 현재 mvp 03 는 기능적으로는 일정 수준 구현된 상태이지만, 코드가 정리되어있지 않고 기능을 추가하는데 있어서 어려움을 겪고 있습니다.    
    - 프론트 디자인이 평범합니다.
    - 각 기능 모듈이 컨벤션이 없습니다.
    - 메모리를 참조하기 보단, 코드와 docs의 03 주제와 관련된 문서를 참조합니다. (SSOT)
    - 01 02와 관련된 문서는 절대 참조하지 않습니다.

    [리팩토링 계획]
    FinAI/ 하위 폴더를 새로 만들어서 JB marker 를 생성한 뒤, Dojaegyum 의 private 으로 git init 합니다.

    # 핵심 아키텍쳐
     - front 구조:  랜딩 페이지 - 콕핏 페이지 - 각 파이프라인 스텝에 따른 기능페이지
     - back 구조: 콕핏 - 기능 페이지 - marker API - 백그라운드 폴더 트리
     1. Front 명세
       @DESIGN.md 는 중앙 디자인 시스템 입니다. 디자인 패턴이 명시되지 않는 경우에는 반드시 디자인 시스템에 맞게 구현됩니다.
       [1] 랜딩 페이지
        - @LANDING.md  의 디자인을 이용합니다. 단 중앙에 랜더 되는 멘트는, '금융 마케팅을 쉽게' 처럼 해커톤 주제에 맞는 멘트로 변경합니다.  
        - @NAVIAGTE.md 의 디자인을 이용합니다. 이것은 네비게이트 메뉴를 위한 디자인 입니다. 메뉴에는 '파이프라인 소개', '연동가능한 앱', '결제', '체험해보기' 등이 있습니다.
        - 중앙에는 '체험해보기' 버튼과 함께 콕핏으로 이동할 수 있는 버튼이 있습니다.
        - JB marker 의 소개글과 이용방식을 작성하는 UI를 디자인과 정합하게 만들어두고, 추후 사용자와 논의 후 텍스트를 집어 넣습니다.        
  
       [2-1] 콕핏 페이지
        - 현재 mvp 03의 콕핏 컴포넌트를 전부 별도의 페이지로 분리하고, 사이드바에서 네비게이트 가능하게 합니다.
        - 사이드바의 요소는 'Workspace', 'History' ,'Setting' 으로 분리합니다.
        - WorkSpace 에는 파이프라인을 Start 할 수 있는 UI, 현재 작업의 현황을 볼 수 있는 프로세스 바, 비주얼 컴패니언 및 에디터, 챗 인터페이스, 중간 과정 아티팩트, 리서치 자료 및 참고자료 뷰어 가 있습니다.
        - JB marker 는 수동 편집과 에이전트 편집이 둘다 가능한 멀티 기능 에디터입니다. 웹에서 수동조작을 하기 위해서는 VSCode나 Antigravity 같은 코드 에디터 처럼 큰 화면을 지원해야합니다. (mvp 03 처럼 작은 에디터 X, 굉장히 불편함.)
        - 콕핏의 Workspace 에서 'Use Marker'를 누르면 BrainStormingStudio 로 이동합니다. (콕핏페이지를 대체하는 방식이 아니라 하나의 탭이 생성되는 방식. 나머지 스텝에 대응되는 Studio에 대해서도 동일 적용.) 프로세스 바는 그에 맞게 갱신됩니다.
  
       [2-2] 기능 페이지
        - BrainStormingStudio/DesignStudio/ReviewStudio/DeployStudio 를 구현합니다.
        
        [2-2-1] BrainStormingStudio  (백엔드 상세: @brainstorm_subharness.md)
         - 현재 mvp 03에서 랭그래프로 구현된 정적 과정에서 고도화를 원합니다. 랭그래프를 쓰지 않아도 좋습니다.
         - 브레인 스토밍 페이지의 왼쪽패널에는 해당 작업을 위한 가상 샌드박스 폴더 트리가 존재합니다. 폴더 내부의 파일은 클릭 시 챗 인터페이스에 오버레이 되어 사용자가 파일내용을 볼 수 있도록 합니다. (당연히 닫기 버튼이 있어야 합니다.)
         - 챗 인터페이스의 아래쪽 입력 패널에는 파일 선택, 전송, 모델 선택 UI를 배치합니다.
         - 모델 선택 UI 는 Claude, GPT, Gemini를 선택할 수 있도록 합니다. 가장 위에는 'Marker'라는 모델을 배치합니다. Marker는 Claude 기반 우리의 하네스가 씌워진 모델입니다. (금융 마케팅 홍보물 기획 하네스)
         - 현재 mvp 03은 오른쪽 패널에 Json 형태로 최종 산출물을 보여주는 반면, JB Marker 는 현재 작업물을 가상 폴더 트리에서 즉각 반영합니다. 자세한 내용은 Back 명세를 참조합니다.
         - 브레인스토밍 1단계 에서 스펙이 만들어집니다. 리서칭 기능은 1단계에서 이용되고, 사용자가 가상 폴더 트리에 수동으로 asset을 추가할 수 있습니다.
         - 브레인스토밍 결과의 스펙은 반드시 리서치한 asset과 브레인스토밍을 기반으로 md 파일로 만들어지며, 이 스펙은 brainstorming 2단계에서 구현계획 md 의 기반이 됩니다.
         - 브레인스토밍 2단계는 스펙을 보고 DesignStudio에서 이용할 수 있는 구현계획을 생성합니다. AI-optimal 하게 구현계획 md 파일을 생성해서 가상 폴더 트리에 등록합니다.
         - 브레인스토밍 과정 중 API 모델에서 사용자에게 보낼수 있는 AskUser 훅을 구현합니다. 중간 미들웨어 웹소켓 리시버를 두고, 질문 사항들에 대해서는 Claude Code 처럼 선택 UI를 웹에 렌더합니다. 이유는 중간 과정의 의사결정과 최종 확정 확인을 위해서입니다. 
         - 스펙과 구현계획이 최종 확정되면, 콕핏으로 유도해 중간과정을 검토하고, DesignStudio 로 넘어갈 수 있도록 중간 경유 과정을 둡니다. (예시: Design 시작하기 버튼 UI/팝업 등)

        [2-2-2] DesignStudio  (백엔드 상세: @design_subharness.md)
         - 디자인 스튜디오에서도 현재 작업에 대한 가상 폴더트리 패널을 유지합니다. 
         - 다국적 타겟 홍보물임이 구현계획과 스펙에 명시되어 있는 경우, 다른 언어버전의 산출물을 가상 폴더에 각각 저장합니다.
         - 큰 에디터와 함께, Antigravity 와 같이 AI 챗 패널을 오른쪽에 둡니다. 
         - 폴더의 파일을 클릭 시, 파일의 내용은 에디터에 오버레이 됩니다. (닫기 기능 당연히 있어야 함.)
         - 디자인 구현계획을 바탕으로 rough -> 각 컴포넌트에 따른 단계 -> final confirm 과정을 통해 디자인을 진행합니다. AI의 디자인 서브 파이프라인은 Back 명세를 참조합니다. 에디터는 가상 폴더 트리에 저장할 수 있는 기능이 항상 동반됩니다. 
         - 디자인 완료가 되면 확정이 되면 UI를 통해 수동 액션을 제공하고, 콕핏 페이지로 돌아갈 수 있도록 합니다. 
         - ReviewStudio가 이미지나 영상 홍보물을 검토하기 수월하도록, 최종 산출물 내부의 텍스트와 콘티를 정리한 메타데이터 파일을 저장해둡니다. 

        [2-2-3] ReviewStudio  (백엔드 상세: @review_subharness.md)
         - mvp 02의 아이디어의 확장 버전입니다. 스펙에 다국적을 대상으로 한 홍보물임이 명시되어 있는 경우 준법 검토뿐만 아니라 다국어 동등성 검토를 시행합니다. 
         - 준법검토는 실제 법률을 기반으로 시행되며, 어떤 부분이 위반이 되었는지 명확한 포인팅이 요구됩니다. DesignStudio의 산출물은 이미지와 영상이기에 디자인 최종 확정 후 미리 만들어 놓은 메타데이터를 참고 + 비전 AI를 통한 검수로 완벽한 검수를 진행합니다. 
         - 다국어 동등성 테스트도 가상 폴더에 각각 저장된 홍보물의 메타데이터를 참고하여 정합성을 판단합니다. 
         - 각 검토는 프로세스 바 UI가 있어야 하고, 사용자가 진행도를 알 수 있도록 % 게이지 UI 를 토스트합니다. 
         - 지금처럼 아래쪽에는 수정되어야 할 부분과 그 근거가 제시됩니다. 아래에 부드럽게 페이드 인 됩니다. 
         - 준법 검토와 다국어 동등성 검토 결과에 대한 수정은 사용자에게 위임됩니다. 수정 후 재검토를 할 수 있도록 콕핏 프로세스 바에  재검토 요청 팝업이 나타납니다. 

        [2-2-4] DeployStudio  (백엔드 상세: @deploy_studio.md)
         - 규칙엔진(정보통신망법 §50: 동의·야간·옵트아웃) + 발송 어댑터(stub). **AI 하네스 아님.** 범위=적법성+발송계획+채널 export까지, 실제 발송은 stub/시뮬.
         - 외부 가용 프로바이더 SVG 로고 그리드('연동가능한 앱'과 동일 소스) + 발송 어드바이저 챗(일반 Claude, **비권위적**: §50·발송·콘텐츠 변경 불가, 조언만).
         - ReviewStudio(콘텐츠 적법성)와 구분: DeployStudio=발송 행위 적법성. 상세 @deploy_studio.md.

       [3] History 페이지
        - History 페이지는 하나의 작업과정에서 발생한 아티팩트와 기반 문서를 볼 수 있습니다.
        - Backend 에서 정의된 가상 폴더 트리에 저장된 각 아티팩트를 의미에 맞게 정렬하고, 사용자가 쉽게 볼 수 있도록 합니다. 
        - 특히 디자인 시스템이 정의되어 있는 것은 iframe으로 프리뷰를 띄울 수 있도록 합니다. 

     2. Back 명세
      
       # 백에서 반드시 정의되어야 하는 기획
        * Marker 모델 (브레인 스토밍/ 디자인)하네스 정의 → @brainstorm_subharness.md · @design_subharness.md ③
        * 디자인 서브 파이프라인 정의 → @design_subharness.md ②
        * 모델 교차 이용 방식/ 에디터 SDK 선택 → @design_subharness.md ① (3액터: Marker·Gemini·IMG.LY CE.SDK)
        * 가상 폴더트리 구조 CRUD 방식 → @vfs.md (트리 SSOT) · @marker_api.md (저장 매개체·CRUD·오케스트레이션)

---

# 백엔드 상세 설계 문서 인덱스 (리팩토링 시작 세션용)

> 아래 `@문서`들은 위 기획을 **구현 가능한 수준으로 구체화한 백엔드 설계 SSOT**다. 리팩토링 시작 시 먼저 정독한다.
> 작성: 2026-05-25 · 범위: 구조 결정(코드 아님) · 근거: mvp/03-marketing 코드 + docs/03 (01·02 비참조).

## 문서 ↔ 기획 매핑

| 문서 | 무엇 | 대응 |
|---|---|---|
| @brainstorm_subharness.md | BrainStorming Marker 하네스 (2스테이지 spec→plan · AskUser 토스트 · 기획자 페르소나 · DesignStudio 정합 계약검증) | 2-2-1, 백기획#1 |
| @design_subharness.md | DesignStudio Marker 하네스 (3액터 · S0~S3 파이프라인 · IMG.LY 구조화 씬 · 크리틱 패스) | 2-2-2, 백기획#1·2·3 |
| @review_subharness.md | ReviewStudio (R1 법률·R2 다국어동등성·R3 통합 · critical→BLOCK 게이트 · 권장만, 수정 안 함) | 2-2-3 |
| @deploy_studio.md | DeployStudio (§50 규칙엔진 + 발송 어댑터 stub · 프로바이더 SVG · 어드바이저 챗 · **하네스 아님**) | 2-2-4 |
| @vfs.md | 가상 폴더트리 SSOT (/{runId}/{studio}/... · manifest + sidecar 메타) | 백기획#4 |
| @marker_api.md | 저장 매개체(Supabase) + Marker API(내부 VfsStore CRUD + AI 게이트웨이) + **오케스트레이션** | 백기획#4, 핵심아키텍처 |
| @navigate.md | 스튜디오 네비게이션 (프로세스바=네비게이터 · manifest 상태 게이팅) | 콕핏 ↔ 기능페이지 이동 |
| @../specs/2026-06-10-harness-correction-openapi-design.md | T1 하네스 원리 교정 + OpenAPI 명세화 (GateEnvelope 게이트 봉투 · PromptSpec · is_entitled choke · routers 8분할 — 위 설계 문서들의 교정 기준. 점검 보고서 @harness_audit.md · WS 레퍼런스 @ws_protocol.md) | 백기획 전반, 핵심아키텍처 |

## 확정된 핵심 결정 (리팩토링 시 재논의 불필요)

1. **LangGraph 미사용** — 상태 단일주인=Supabase, 진행=수동 네비게이션, 스튜디오=에이전트 루프(클로드 코드식). 근거 @marker_api.md §2.
2. **저장=Supabase**(Postgres=구조/텍스트 · Storage=블롭) 무료 영속. VfsStore 추상화로 로컬/테스트 impl 병행(벤더 락인 없음).
3. **디자인 산출 = IMG.LY CE.SDK 구조화 씬**(평면 PNG 아님) — 다국어·편집·채널 리사이즈의 전제.
4. **3액터** — Marker(Claude 하네스)=디렉션·카피·크리틱 / Gemini=텍스트 없는 비주얼 / IMG.LY=렌더·편집.
5. **DeployStudio는 하네스 아님** — 결정론적 §50 규칙엔진. Review(콘텐츠 적법성) vs Deploy(발송 행위 적법성) 분리.
6. **공유 CRUD 스킬 실체 = VfsStore**(@marker_api.md §3-1) — 3 하네스 공유.

## 데이터 흐름 (단계 간 핸드오프)

`brainstorming` → `spec.md`/`plan.md` → DesignStudio가 `plan.md` 파싱 → `design/final/{lang}` + `metadata.md` → ReviewStudio가 검토 → `review/report.md` + 게이트(critical→BLOCK) → DeployStudio. 모든 단계 @vfs.md 경유 · API/오케스트레이션 @marker_api.md · 이동 @navigate.md.

## 횡단 미결 (구현 단계 결정 — 지금 불필요)

- `spec.md`/`plan.md` 섹션 템플릿(⓪ 계약 강제 양식) · 크리틱 루브릭 · severity(critical/warning) 판정 기준.
- 자동수정/iteration 수신 귀속 (@review_subharness.md③ ↔ @design_subharness.md 미결).
- 레퍼런스(few-shot) · 공식 법령 서칭 소스 · 채널 규격 카탈로그 · `consent_ledger` 출처.
- Supabase 운영(일시정지 핑 · public vs signed URL) · 테스트 동등성 계약(노드 함수 보존, 그래프 테스트 재작성).

## 편집 규약

- 본 인덱스 아래 `@문서`들이 설계 SSOT다. 기획 변경 시 해당 문서 + 본 매핑을 함께 갱신.
- 위 [배경]~[백기획] 원문은 사용자 기획이며 보존됨.

---

# 리팩토링 운영 결정 (스코프 · 완료 · 마이그레이션 · 인프라)

> 위 기획의 빈칸(C1~C4)을 확정하고, 리팩토링 진행에 필요한 메타를 정의한다. 2026-05-25.

## 설계 보강 결정 (C1~C4 — 기존 명세 빈칸 확정)

- **C1 인증** — **Auth 사용.** Supabase Auth 채택(@marker_api.md 저장 스택과 동일 벤더). run · History · 결제는 **사용자 계정에 귀속**(VFS `runs.user_id`).
- **C2 모델 적용 범위** — raw 모델 선택 = **Claude · GPT · Gemini 모두 지원**(AI 게이트웨이 프로바이더, @marker_api.md §3-2). **GPT도 정식 적용.** 'Marker' = Claude 기반 하네스(플래그십, C4 유료).
- **C3 에디터 이중성** — **허용.** 파일 타입별 렌더러 분기: `.md`/`.json` = 텍스트 뷰어(클릭 오버레이·읽기) / `.scene` = IMG.LY CE.SDK 대형 에디터(수동+에이전트 편집).
- **C4 결제** — **인스코프.** 티어 **$100 / 월**, 혜택 = ⓐ **Marker 모델 이용** ⓑ **DeployStudio Advisor 이용**. → 두 기능은 **유료 엔타이틀먼트 게이트** 뒤(무료 = raw Claude/GPT/Gemini만). 검사 위치 = AI 게이트웨이(@marker_api.md §3-2, 단일 choke point).

## Non-goals (이번 리팩토링 비스코프)

- **실제 채널 발송** — DeployStudio는 stub/시뮬/export까지(@deploy_studio.md). 실 dispatch ✗.
- **실 결제 PG 청구** — 결제 티어·엔타이틀먼트는 정의하되, 실 결제 게이트웨이 청구는 데모 stub 가능(미결).
- **01·02 주제 코드/문서 참조** — 영구 비스코프(배경 8~9줄).

## 완료 정의 (DoD)

- 새 JB Marker **배포 후 → 사용자(albert) 수동 검증**으로 최종 마무리.
- 자동 테스트 통과는 **필요조건**이나 충분조건 아님 — 수동 검증이 완료 게이트.

## 마이그레이션 전략 (03 → JB Marker)

- **이관(함수 재사용)**: brainstorm · generate · review · i18n_equiv 노드 로직, `rules_engine`(§50)·`evaluate_recipient`, grounding 검사.
- **버림**: LangGraph 그래프 배선(`graph.py`), 휘발 PlanState, 03의 작은 에디터.
- **상태 이전**: PlanState(휘발) → VFS/Supabase 영속(@marker_api.md §4).
- **테스트**: 노드 함수 단위 보존, 그래프 배선 테스트 재작성.

## 배포 인프라

- 프론트 = **Vercel**(03 계승) · 저장·상태 = **Supabase**(Postgres+Storage) · 인증 = **Supabase Auth** · 백엔드 호스트 = 03 계승(HF Space) 기본, Supabase 연동 시 재검토.