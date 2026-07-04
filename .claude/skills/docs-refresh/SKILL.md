---
name: docs-refresh
description: Use when 코드 변경이 쌓인 뒤 문서를 일괄 갱신할 때 — 마지막 갱신 이후 diff를 스캔해 README·본선 변경 보고서·기능 체인지로그를 실제 코드와 정합하게 갱신. "문서 갱신", "docs refresh", "README 업데이트", "보고서 반영" 트리거.
---

# /docs-refresh — 코드→문서 일괄 정합화

목적: 폭발적 개발 중 문서가 코드에서 멀어지는 것을 방지. **루브릭 4.1(산출물 간 정합성)·4.3(명세 구체성)** 직결.

## 절차

### 1. 갱신 범위 결정
```bash
git log --oneline --grep="docs(refresh)" -1   # 마지막 refresh 커밋 찾기
git log --oneline --stat <마지막refresh커밋>..HEAD   # 그 이후 변경 전부
```
- refresh 커밋이 없으면 사용자에게 시작점을 확인한다.

### 2. 변경 분류
각 커밋을 두 갈래로 분류:
- **순수 최적화**(품질·폴리시·프롬프트·렌더 개선) → `docs/finals/optimization-report.md`에 반영
- **기능 추가/변경(CUD)** — 새 사용자 기능·화면·엔드포인트·옵션 → `docs/finals/feature-changelog.md`에 **필수 기록**(기능명세 제출 대상)

### 3. 문서 갱신
| 문서 | 갱신 내용 |
| --- | --- |
| `README.md` | 기능 목록·아키텍처 서술·테스트 수·라이브 URL이 현재 코드와 일치하는지 |
| `docs/finals/optimization-report.md` | 새 최적화 섹션 추가 + §9 커밋 매핑 표에 행 추가 |
| `docs/finals/feature-changelog.md` | CUD 항목: 무엇을·왜·사용자 가시 변화·관련 커밋 |
| `docs/finals/qa-sheet.md` | 새 변경으로 답변이 달라지는 질문이 있으면 갱신(예: 숫자 카드) |

### 4. 원칙 (과장 배제)
- **코드로 검증된 것만 서술.** 미구현·시뮬레이션·키 의존은 명시.
- 숫자(테스트 수·성능치)는 **재실측한 경우에만** 갱신 — 옛 숫자에 손대지 않았으면 그대로 둔다.
- 자체보고 불신: 커밋 메시지만 믿지 말고 핵심 변경은 diff를 직접 확인.

### 5. 커밋
```bash
git add <갱신한 문서만>
git commit -m "docs(refresh): <범위 요약> 문서 정합화"
```
`docs(refresh)` prefix가 다음 실행의 범위 마커가 된다 — 반드시 이 형식으로.
