def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_run_and_list(client):
    r = client.post("/runs", json={"title": "캠페인"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    g = client.post("/gateway/run", json={
        "run_id": run_id, "studio": "brainstorming",
        "prompt": "아이디어", "provider": "fake", "is_marker": False,
    })
    assert g.status_code == 200
    out_path = g.json()["output_path"]

    lst = client.get(f"/vfs/{run_id}", params={"prefix": f"/{run_id}/brainstorming"})
    assert any(n["path"] == out_path for n in lst.json()["nodes"])

    got = client.get(f"/vfs/{run_id}/brainstorming/passthrough.md")
    assert got.status_code == 200
    assert "아이디어" in got.json()["content_text"]


def test_put_text_via_editor(client):
    run_id = client.post("/runs", json={}).json()["run_id"]
    r = client.put(f"/vfs/{run_id}/design/notes.md", json={"content": "메모"})
    assert r.status_code == 200
    assert client.get(f"/vfs/{run_id}/design/notes.md").json()["content_text"] == "메모"
