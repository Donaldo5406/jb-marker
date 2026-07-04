---
name: ship
description: Use when 작업 브랜치를 main으로 출하할 때 — 검증→push→PR 생성→머지→Dojaegyum 미러 sync까지 한 번에. "출하", "ship", "PR 올려줘", "머지하고 sync"에 트리거. 문서만 바꿨으면 테스트를 스킵한다.
---

# /ship — 출하 자동화 (검증 → PR → 머지 → 미러 sync)

목적: 해커톤 중 반복되는 출하 절차를 표준화하고, **Dojaegyum 미러 sync 누락**(상습 발생)을 원천 차단한다.

## 절차 (순서 엄수)

### 0. 프리플라이트
- 현재 브랜치가 `main`이면 중단 — 작업 브랜치에서만 실행.
- 커밋 안 된 변경이 있으면 먼저 커밋(사용자 확인). 커밋 메시지는 conventional(`feat|fix|docs|chore(scope): ...`).
- 변경 범위 판별: `git diff origin/main...HEAD --name-only`
  - **문서만**(`*.md`·`docs/**`) → 테스트 스킵하고 2로.
  - `backend/**` 포함 → 백엔드 테스트 실행.
  - `frontend/**` 포함 → 프런트 테스트 실행.

### 1. 검증 (해당 영역만)
```bash
cd backend && python -m pytest -q          # 백엔드 변경 시
cd frontend && npm test && npm run typecheck  # 프런트 변경 시
```
실패 시 **중단하고 결과를 보고**한다. 실패 상태로 출하하지 않는다.

### 2. Push + PR
```bash
git pull --rebase origin main   # 충돌 시 해결 후 진행 (rkdrn79와 병렬 작업 중)
git push -u origin <브랜치>
gh pr create --base main --title "<커밋 요지>" --body "<변경 요약>"
```
PR body 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)` 포함.

### 3. 머지
```bash
gh pr merge --squash --delete-branch
```
- ⚠️ **문서가 커밋 SHA를 참조하는 대형 브랜치는 `--merge`**(스쿼시 금지): 예) `feat/finals-optimization`은 optimization-report §9가 개별 SHA를 인용 → 스쿼시하면 보고서 SHA가 고아가 됨.
- squash가 레포 설정에서 막혀 있으면 `--merge`로 폴백.
- CI가 있으면 통과 확인 후 머지(`gh pr checks`).

### 4. main 동기화 + Dojaegyum 미러 sync ← 이 스킬의 존재 이유
```bash
git checkout main && git pull origin main
git remote get-url mirror 2>/dev/null || git remote add mirror https://github.com/Dojaegyum/jb-marker.git
gh auth switch --user Dojaegyum     # 미러는 Dojaegyum 소유 — Donaldo 토큰은 404
git push mirror main
gh auth switch --user Donaldo5406   # 반드시 원복 (origin 작업은 Donaldo)
```
- ⚠️ **첫 sync는 non-fast-forward로 거부될 수 있음**: Donaldo5406 히스토리는 git-filter-repo로 재작성되어 미러(6/14 이전 히스토리)와 divergent. 거부되면 **사용자에게 확인 후** `git push mirror main --force` (미러는 사본이므로 force가 의도된 동작).
- push 성공/실패와 무관하게 **계정을 Donaldo5406으로 원복**했는지 마지막에 확인.

### 5. 배포 확인 + 정리
- `gh run list -L 3` 로 Donaldo Actions CD 트리거 확인 (HF Space·Vercel).
- 워크트리에서 작업했다면: `git worktree remove ../jbm-wt-<주제>`.
- 최종 보고: PR URL · 머지 커밋 SHA · 미러 sync 여부 · CD 상태 를 한 줄씩.

## 하지 말 것
- 테스트 실패·CI red 상태로 머지 금지.
- main 직접 push 금지 (미러 제외).
- 미러 force push를 사용자 확인 없이 실행 금지.
