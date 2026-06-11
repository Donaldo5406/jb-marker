"""openapi.json 계약 단언 (spec §10) — /docs가 진짜 명세임을 기계 검증."""
import pytest
from typing import get_args

from app.server import create_app


@pytest.fixture(scope="module")
def spec():
    return create_app().openapi()


def test_security_scheme_exists(spec):
    schemes = spec["components"]["securitySchemes"]
    assert any(s.get("type") == "http" and s.get("scheme") == "bearer"
               for s in schemes.values())


def test_protected_routes_declare_security(spec):
    op = spec["paths"]["/gateway/run"]["post"]
    assert op.get("security"), "인증 의존 라우트에 security 표기 누락"


def test_all_eight_tags_present(spec):
    declared = {t["name"] for t in spec.get("tags", [])}
    used = set()
    for path in spec["paths"].values():
        for op in path.values():
            if isinstance(op, dict):
                used.update(op.get("tags", []))
    expected = {"meta", "runs", "gateway", "session", "vfs", "deploy",
                "observability", "history"}
    assert expected <= declared
    assert expected <= used
    assert used <= declared, f"미선언 태그 사용: {used - declared}"


def test_gateway_literals_exposed(spec):
    gw = spec["components"]["schemas"]["GatewayRun"]["properties"]
    assert set(gw["studio"]["enum"]) == {"brainstorming", "design", "review", "deploy"}
    assert set(gw["provider"]["enum"]) == {"fake", "demo", "anthropic", "openai", "google"}


def test_response_schemas_nonempty(spec):
    """주요 엔드포인트 200 응답에 비공백 스키마가 선언됐는가."""
    for path, method in [("/health", "get"), ("/runs", "post"), ("/runs", "get"),
                         ("/gateway/run", "post"), ("/entitlement", "get"),
                         ("/runs/{run_id}/usage", "get"), ("/runs/{run_id}/gallery", "get")]:
        op = spec["paths"][path][method]
        content = op["responses"]["200"]["content"]["application/json"]
        assert content.get("schema"), f"{method.upper()} {path} 응답 스키마 공백"


def test_error_responses_documented(spec):
    op = spec["paths"]["/gateway/run"]["post"]
    assert "402" in op["responses"] and "404" in op["responses"]


def test_session_heartbeat_exposes_both_variants(spec):
    """smart union — 두 변형이 스키마에 노출(anyOf/oneOf 구체 형태엔 비결합)."""
    op = spec["paths"]["/runs/{run_id}/session/{studio}"]["get"]
    blob = str(op["responses"]["200"]["content"]["application/json"]["schema"])
    assert "SessionLivenessOut" in blob and "SessionMissingOut" in blob


# ── Literal SSOT 동기화 — 수동 손복사 어휘의 자기강제 (T8 리뷰 Important) ──

def test_studio_literal_matches_lifecycle_studios():
    from app.routers.gateway import GatewayRun
    from app.vfs.types import LIFECYCLE_STUDIOS
    assert set(get_args(GatewayRun.model_fields["studio"].annotation)) == set(LIFECYCLE_STUDIOS)


def test_provider_literal_matches_registry():
    """Literal 어휘 전수가 registry에서 ValueError 없이 해석돼야 — 정합 가드.
    (live provider 생성자는 lazy import — 키 없이 인스턴스화 가능, 네트워크 비발생)
    단방향 가드(Literal⊆registry) — registry가 if-체인이라 역방향은 불가(이월)."""
    from app.routers.gateway import GatewayRun
    from app.providers.registry import get_provider
    from app.config import load_settings
    names = set(get_args(GatewayRun.model_fields["provider"].annotation))
    s = load_settings()
    for name in names:
        get_provider(name, s)
