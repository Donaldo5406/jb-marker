"""design 카피(S2b) 게이트에서 챗 교정 피드백 → 위반→clean 카피 재생성(통합 회귀 잠금).

부품: pipeline (b)분기(게이트 중 user_prompt면 현재 step 재실행) + S2bCopy.run(req.user_prompt를
demo에 전달) + demo._copy_json(교정 신호 → F.COPY). 디자인 챗 위반→교정 루프가 end-to-end로
성립하는지 확인 — 라이브에서 안 먹던 시나리오의 백엔드 동작 확정.
"""
from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.server import create_app
    return TestClient(create_app())


def _headline_ko(client, rid):
    return client.get(
        f"/vfs/{rid}/design/design-system/components/headline/ko.txt"
    ).json()["content_text"]


def test_design_chat_feedback_remediates_copy(monkeypatch):
    client = _client(monkeypatch)
    rid = client.post("/runs", json={}).json()["run_id"]

    def design(prompt="", action=None):
        body = {"run_id": rid, "studio": "design", "prompt": prompt,
                "provider": "anthropic", "is_marker": True, "mock": True}
        if action:
            body["action"] = action
        return client.post("/gateway/run", json=body)

    # 파이프라인 step 순서 = S0·S1(Rough)·S2b(카피)·S2a(비주얼)·S2c·S3 — 카피가 비주얼보다 먼저.
    design(action="advance")        # S0→S1(Rough) 게이트
    r = design(action="advance")    # S1 승인 → S2b(카피) 게이트 — 1차 카피(의도적 위반)
    assert r.status_code == 200
    assert "국내유일" in _headline_ko(client, rid)   # 1차 = 위반 카피

    # 게이트 상태에서 챗 교정 피드백(action 없음, user_prompt에 교정 신호) → S2b 재실행.
    r2 = design(prompt="과장 표현 빼고 준법 표현으로 카피를 교정해줘")
    assert r2.status_code == 200
    ko = _headline_ko(client, rid)
    assert "국내유일" not in ko        # 위반 표현 제거
    from app.providers.demo_fixtures import COPY
    assert ko == COPY["ko"]["headline"]   # clean 카피로 교체
