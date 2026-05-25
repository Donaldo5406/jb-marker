# 스튜디오 네비게이션 설계 (Studio Navigation)

> 대상: @Refactor.md 미정의 영역 — 기능 페이지(스튜디오) 간 이동 방식.
> 주의: 랜딩 네비게이트 **메뉴 디자인**(@NAVIAGTE.md, Refactor 21줄)과 **별개**. 이 문서는 콕핏·스튜디오 내부 네비게이션 규칙.
> 범위: 구조 결정만. 코드 구현 아님.
> 작성일: 2026-05-25 · SSOT: mvp/03-marketing + docs/03 (01·02 비참조)

---

## 0. 결정: 모델 C — 프로세스 바 = 네비게이터 겸용

별도 네비게이션 패널을 **신설하지 않는다**(콕핏·탭·프로세스 바와 기능 중복). 이미 정의된 **프로세스 바를 클릭 가능한 네비게이터로 승격**한다.

- 근거: Refactor **30줄**(스튜디오는 콕핏과 공존하는 **탭** + 프로세스 바 갱신), **45줄**(forward 시 **콕핏 경유 검토 유도**).

## ① 구성 요소

- **콕핏 = 허브 탭** — 항상 접근 가능. 전체 조망·시작점.
- **스튜디오 탭** — brain / design / review / deploy. `Use Marker` 등으로 생성(Refactor 30줄).
- **프로세스 바** — 상단 스텝 인디케이터 **겸 네비게이터**:

```
[ brain ] → [ design ] → [ review ] → [ deploy ]      (각 스텝 클릭 = 해당 탭으로 점프)
```

## ② 이동 정책

| 방향 | 규칙 | 근거 |
|---|---|---|
| **forward**(다음 단계) | 단계 완료 → **콕핏 경유 검토** → 다음 스튜디오 (예: "Design 시작하기" 버튼/팝업) | Refactor 45줄 검토 유도 유지 |
| **backward / iteration** | 이미 연 스튜디오로 **직접 이동**(콕핏 생략) | ReviewStudio iteration 마찰 제거 |
| **콕핏 복귀** | 어느 시점이든 허브 탭으로 복귀 | 전체 조망 |

## ③ 상태 게이팅 (@vfs.md manifest 연동)

이동 가능 여부 = `manifest.step_status` + 각 스튜디오 게이트.

- **forward**: 이전 단계가 완료/승인돼야 다음 탭 **활성화**.
- **BLOCK 잠금**: review가 critical(BLOCK)이면 **deploy 탭 잠금** (@review_subharness.md 게이트와 연결).
- **backward**: 이미 연 스튜디오로는 **항상 자유 이동**(iteration 지원).

## ④ ReviewStudio iteration 대표 흐름

```
review (권장 확인) ─직접→ design (수정) ─직접→ review (재검토) ─ … critical 해소까지 반복
                       └ 콕핏 경유 없음 (backward 직접 이동)
```

## 미결 / 후속 결정 항목

- 프로세스 바에서 **미완료/잠금 단계 시각 표현**(비활성·자물쇠 등).
- 탭 **닫기/재열기** 정책.
- **deploy 진입 조건** (DeployStudio 명세 확정 후).
