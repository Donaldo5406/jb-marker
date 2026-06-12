"""routers 공유 의존성 — 전부 request.app.state 경유 (spec §8.1).

모듈 싱글턴 금지: 거의 모든 테스트가 `setenv → create_app()` 패턴으로
앱 인스턴스별 fresh 상태(settings·store)에 의존한다.

인증: HTTPBearer(auto_error=False)는 OpenAPI securitySchemes 표기와
Swagger Authorize 버튼 활성화 전용이다. 실제 검증은 종전대로
auth.resolve_user_id(raw Authorization 헤더)가 수행한다 — 보존해야 할
행동 3가지: ① local 모드는 헤더 무시·무조건 "demo" ② 스킴 없는 생토큰
수용 ③ 토큰 부재 401 detail. (auth.py는 불변)

예외: entitlement는 의도된 모듈 싱글턴(create_app가 set_store로 매번 교체 —
test_entitlement_choke 의미론). app.state로 옮기지 말 것.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..auth import resolve_user_id
from ..observability import tracing

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_id(
    request: Request,
    # OpenAPI 표기 전용 — 값 미사용(검증은 resolve_user_id)
    _cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    return resolve_user_id(request.headers.get("authorization"),
                           request.app.state.settings)


def require_owner_factory(store):
    """run 소유권 가드. 소유자 불일치/부재 → 404(존재 노출 회피)."""

    def _guard(run_id: str, user_id: str):
        m = store.get_manifest(run_id)
        if m is None or m.user_id != user_id:
            raise HTTPException(404, "run not found")
        return m
    return _guard


def require_owner(request: Request, run_id: str, user_id: str):
    tracing.tag_run(run_id, request.app.state.settings)
    return require_owner_factory(request.app.state.store)(run_id, user_id)
