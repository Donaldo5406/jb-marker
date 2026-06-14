"""영상 파이프라인 Mock e2e(HTTP) — /gateway/run(mock=true, studio=video)로 V0→done + render.

사용자 명시 요구: 새 영상 파이프라인(V0~V3·렌더) Mock 테스트. 키/ffmpeg 없이(demo + stub)
콘티·footage·메타·최종 mp4·고지 422·브레인스토밍 medium=video까지 회귀 잠금.
"""
import json


def _client(monkeypatch):
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("MARKER_DISABLE_FFMPEG", "1")  # stub mp4(ffmpeg 부재 무관)
    from app.server import create_app
    from fastapi.testclient import TestClient
    return TestClient(create_app())


def _new_run(client):
    return client.post("/runs", json={}).json()["run_id"]


def _seed_video_plan(client, rid):
    from app.providers import demo_fixtures as F
    r = client.put(f"/vfs/{rid}/brainstorming/plan.md",
                   json={"content": F.VIDEO_PLAN_MD, "mime": "text/markdown"})
    assert r.status_code in (200, 201), r.text


def _run_video(client, rid, prompt="영상 시작", **kw):
    body = {"run_id": rid, "studio": "video", "prompt": prompt,
            "provider": "anthropic", "is_marker": True, "mock": True}
    body.update(kw)
    return client.post("/gateway/run", json=body)


def _drive_to_done(client, rid):
    bypass = {s: True for s in ("V1", "V2a", "V2b", "V2c", "V3")}
    r = _run_video(client, rid, action="advance", bypass_map=bypass)
    assert r.status_code == 200, r.text
    res = r.json()
    for _ in range(12):
        if (res.get("meta") or {}).get("step") == "done":
            break
        r = _run_video(client, rid, prompt="", action="advance")
        assert r.status_code == 200, r.text
        res = r.json()
    return res


def test_video_pipeline_v0_to_done_mock(monkeypatch):
    client = _client(monkeypatch)
    rid = _new_run(client)
    _seed_video_plan(client, rid)
    res = _drive_to_done(client, rid)
    assert (res.get("meta") or {}).get("step") == "done", res
    for rest in ["video/design-system/tokens.json",
                 "video/storyboard/storyboard.spec.json",
                 "video/design-system/components/footage/clip_s1.mp4",
                 "video/metadata.md"]:
        assert client.get(f"/vfs/{rid}/{rest}").status_code == 200, rest


def test_video_render_action_produces_final_mp4_mock(monkeypatch):
    client = _client(monkeypatch)
    rid = _new_run(client)
    _seed_video_plan(client, rid)
    _drive_to_done(client, rid)
    r = _run_video(client, rid, prompt="", action="render")
    assert r.status_code == 200, r.text
    assert client.get(f"/vfs/{rid}/review/_render/final.mp4").status_code == 200


def test_video_render_422_on_short_disclosure(monkeypatch):
    client = _client(monkeypatch)
    rid = _new_run(client)
    _seed_video_plan(client, rid)
    _drive_to_done(client, rid)
    sb = json.loads(
        client.get(f"/vfs/{rid}/video/storyboard/storyboard.spec.json").json()["content_text"])
    for shot in sb.get("shots", []):
        shot["layers"] = [l for l in shot.get("layers", []) if l.get("role") != "disclosure"]
    client.put(f"/vfs/{rid}/video/storyboard/storyboard.spec.json",
               json={"content": json.dumps(sb), "mime": "application/json"})
    r = _run_video(client, rid, prompt="", action="render")
    assert r.status_code == 422, r.text


def test_brainstorm_video_spec_has_medium(monkeypatch):
    client = _client(monkeypatch)
    rid = _new_run(client)

    def turn(prompt, answer=None):
        body = {"run_id": rid, "studio": "brainstorming", "prompt": prompt,
                "provider": "anthropic", "is_marker": True, "mock": True, "medium": "video"}
        if answer is not None:
            body["answer"] = answer
        r = client.post("/gateway/run", json=body)
        assert r.status_code == 200, r.text
        return r

    turn("정기예금 영상 캠페인 기획하자")
    turn("2030 사회초년생", answer="2030 사회초년생")
    turn("국문만", answer="국문만")  # turns>=3 → demo가 VIDEO_SPEC_MD(medium:video) 작성
    spec = client.get(f"/vfs/{rid}/brainstorming/spec.md")
    assert spec.status_code == 200, spec.text
    assert "medium: video" in spec.json()["content_text"]
