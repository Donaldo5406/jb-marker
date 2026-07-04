# backend/tests/test_review_highlight.py
from app.gateway.review_highlight import (
    canvas_of, slot_to_bbox_norm, reviewed_image_for, clamp01,
)

LAYOUT = {
    "slots": [
        {"role": "background", "bbox": {"x": 0, "y": 0, "w": 1080, "h": 1350}},
        {"role": "headline", "bbox": {"x": 80, "y": 160, "w": 920, "h": 200}},
        {"role": "disclosure", "bbox": {"x": 80, "y": 1276, "w": 920, "h": 58}},
    ]
}

def test_canvas_of_reads_background_slot():
    assert canvas_of(LAYOUT) == (1080, 1350)

def test_canvas_of_defaults_when_missing():
    assert canvas_of({"slots": []}) == (1080, 1350)

def test_slot_to_bbox_norm_headline():
    b = slot_to_bbox_norm("headline", LAYOUT)
    assert b == {"x": 80/1080, "y": 160/1350, "w": 920/1080, "h": 200/1350}

def test_slot_to_bbox_norm_unknown_slot_is_none():
    assert slot_to_bbox_norm("nope", LAYOUT) is None

def test_reviewed_image_for_scene_maps_to_baked_visual():
    assert reviewed_image_for("design/final/ko/main.scene", "ko") == \
        "design/design-system/components/visual/v1.png"

def test_reviewed_image_for_png_passthrough():
    assert reviewed_image_for("review/uploads/poster.png", None) == \
        "review/uploads/poster.png"

def test_clamp01():
    assert clamp01(-0.2) == 0.0 and clamp01(1.4) == 1.0 and clamp01(0.5) == 0.5


from app.gateway.review_highlight import build_highlight_html

def _rects():
    return [
        {"x": 0.074, "y": 0.118, "w": 0.5, "h": 0.15, "severity": "critical", "pin": 1},
        {"x": 0.074, "y": 0.945, "w": 0.85, "h": 0.043, "severity": "warning", "pin": 2, "label": "고지"},
    ]

def test_build_html_is_self_contained_data_uri():
    out = build_highlight_html(b"\x89PNG\r\n", "image/png", _rects())
    assert out.startswith("<!doctype html>")
    assert "data:image/png;base64," in out
    # 외부 리소스 금지(네트워크 요청 0)
    assert "http://" not in out and "https://" not in out

def test_build_html_places_each_rect_percent():
    out = build_highlight_html(b"x", "image/png", _rects())
    assert "left:7.4%" in out and "top:11.8%" in out and "width:50%" in out
    assert "class=\"hl crit\"" in out and "class=\"hl warn\"" in out

def test_build_html_renders_pins():
    out = build_highlight_html(b"x", "image/png", _rects())
    assert ">1<" in out and ">2<" in out

def test_build_html_empty_rects_shows_image_only():
    out = build_highlight_html(b"x", "image/png", [])
    assert "class=\"hl" not in out and "data:image/png;base64," in out


from app.gateway.review_highlight import resolve_location

FIX = {("design/design-system/components/visual/v1.png", "headline", "ko"):
       {"x": 0.074, "y": 0.12, "w": 0.62, "h": 0.075}}

def test_resolve_uses_authored_fixture_first():
    loc = {"slot": "headline", "lang": "ko"}
    out = resolve_location(loc, asset_id="design/final/ko/main.scene", lang="ko",
                           layout_spec=LAYOUT, fixtures=FIX)
    assert out["image"] == "design/design-system/components/visual/v1.png"
    assert out["bbox"] == {"x": 0.074, "y": 0.12, "w": 0.62, "h": 0.075}

def test_resolve_falls_back_to_slot_bbox():
    loc = {"slot": "disclosure", "lang": "ko"}
    out = resolve_location(loc, asset_id="design/final/ko/main.scene", lang="ko",
                           layout_spec=LAYOUT, fixtures={})
    assert out["bbox"] == slot_to_bbox_norm("disclosure", LAYOUT)

def test_resolve_keeps_existing_bbox_from_vision():
    loc = {"slot": "visual", "lang": None, "bbox": {"x": .1, "y": .1, "w": .2, "h": .2}}
    out = resolve_location(loc, asset_id="x.png", lang=None, layout_spec={}, fixtures={})
    assert out["bbox"] == {"x": .1, "y": .1, "w": .2, "h": .2}

def test_resolve_no_bbox_when_unresolvable():
    loc = {"slot": "nope", "lang": "ko"}
    out = resolve_location(loc, asset_id="design/final/ko/main.scene", lang="ko",
                           layout_spec=LAYOUT, fixtures={})
    assert "bbox" not in out and out["image"] == "design/design-system/components/visual/v1.png"


# --- Task 4: collect_rects / pin_sort_key — 라우트 헬퍼 단위 테스트 ---------
from app.gateway.review_highlight import collect_rects, pin_sort_key

def test_pin_sort_key_orders_critical_first():
    vs = [{"severity": "warning", "verdict_id": "b"},
          {"severity": "critical", "verdict_id": "z"},
          {"severity": "critical", "verdict_id": "a"}]
    ordered = sorted(vs, key=pin_sort_key)
    assert [v["verdict_id"] for v in ordered] == ["a", "z", "b"]

def test_collect_rects_filters_by_image_and_bbox_and_numbers():
    verdicts = [
        {"verdict_id": "v1", "severity": "critical",
         "location": {"image": "p.png", "bbox": {"x": .1, "y": .1, "w": .2, "h": .1}}},
        {"verdict_id": "v2", "severity": "warning",
         "location": {"image": "p.png"}},                       # bbox 없음 → 제외
        {"verdict_id": "v3", "severity": "warning",
         "location": {"image": "other.png", "bbox": {"x": 0, "y": 0, "w": 1, "h": 1}}},
    ]
    rects = collect_rects(verdicts, "p.png")
    assert len(rects) == 1
    assert rects[0]["pin"] == 1 and rects[0]["severity"] == "critical"
    assert rects[0]["x"] == .1


# --- 라우트 통합(TestClient) — GET /runs/{run_id}/review-highlight ---------
# 리뷰 Minor 후속: 헬퍼 단위 테스트만 있고 라우트 자체 테스트가 없던 갭을 메운다.
# test_history_preview.py의 형제 라우트(GET /runs/{run_id}/preview) 테스트와
# 동일한 TestClient + app + store 셋업을 그대로 따른다.
import base64
import json as _json

from fastapi.testclient import TestClient

from app.server import create_app

_VISUAL = "design/design-system/components/visual/v1.png"


def _seed_visual(client, run_id, *, png=b"\x89PNG\r\n\x1a\nFAKE"):
    client.put(f"/vfs/{run_id}/{_VISUAL}",
               json={"content": base64.b64encode(png).decode("ascii"),
                     "mime": "image/png", "content_encoding": "base64"})


def _seed_verdict(client, run_id, *, verdict_id="legal_0a1b2c3d_headline_ko",
                  severity="critical", image=_VISUAL):
    verdict = {
        "verdict_id": verdict_id, "node": "legal", "severity": severity,
        "location": {"slot": "headline", "image": image,
                     "bbox": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.15}},
    }
    client.put(f"/vfs/{run_id}/review/legal/headline/verdict.json",
               json={"content": _json.dumps(verdict, ensure_ascii=False),
                     "mime": "application/json"})


def test_review_highlight_route_returns_overlay_html_for_owner():
    c = TestClient(create_app())
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    _seed_visual(c, run_id)
    _seed_verdict(c, run_id)
    r = c.get(f"/runs/{run_id}/review-highlight", params={"image": _VISUAL})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'class="hl' in r.text                # bbox 오버레이 존재
    assert "data:image/png;base64," in r.text   # 포스터 인라인


def test_review_highlight_route_missing_image_is_image_only_fallback():
    c = TestClient(create_app())
    run_id = c.post("/runs", json={"title": "n"}).json()["run_id"]
    # 이미지 노드를 심지 않음 — node=None 폴백 경로(빈 rects)
    r = c.get(f"/runs/{run_id}/review-highlight", params={"image": _VISUAL})
    assert r.status_code == 200
    assert 'class="hl' not in r.text
    assert "data:image/png;base64," in r.text   # 빈 바이트라도 data URI 골격은 유지


def test_review_highlight_route_404_for_missing_run():
    c = TestClient(create_app())
    r = c.get("/runs/nope/review-highlight", params={"image": _VISUAL})
    assert r.status_code == 404


def test_review_highlight_route_404_for_non_owner(monkeypatch, tmp_path):
    """로컬 모드는 요청자 user_id가 항상 'demo' — 다른 소유자의 run을 요청하면
    404(존재 자체를 노출하지 않음). test_owner_guard_sweep.py와 동일한 방식으로
    스토어에 직접 타인 소유 run을 심어 owner-vs-non-owner를 구성한다."""
    monkeypatch.setenv("VFS_BACKEND", "local")
    monkeypatch.setenv("JBM_STORAGE_DIR", str(tmp_path))
    app = create_app()
    c = TestClient(app)
    app.state.store.create_run("foreign_rh", user_id="alice", title=None, languages=[])
    r = c.get("/runs/foreign_rh/review-highlight", params={"image": _VISUAL})
    assert r.status_code == 404
