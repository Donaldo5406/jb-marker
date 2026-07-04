"""티키타카 드라이버 — 게이트 ON 파이프라인을 턴 단위로 조작.
사용: python tikitaka.py <port> new
      python tikitaka.py <port> turn "<prompt>" [advance|regenerate]
      python tikitaka.py <port> preview <이름>   # preview.html 저장+요약
      python tikitaka.py <port> spec             # layout.spec 요약
      python tikitaka.py <port> poster <이름>    # v1.png 저장
"""
import json
import pathlib
import sys
import urllib.request

SP = pathlib.Path(__file__).parent
STATE = SP / "tk_state.json"
H = {"Content-Type": "application/json"}


def req(method, url, body=None, raw=False, timeout=900):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=H)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        b = resp.read()
        return b if raw else b.decode("utf-8", "replace")


PLAN = """---
medium: image
languages: [ko]
copy_themes: ["첫 목돈의 시작", "청년 우대금리", "지금 시작하는 스마트한 저축 습관"]
creative_direction:
  concept: "골든아워의 도심 루프탑 카페 — 20대 커플이 노트북과 커피잔을 두고 환하게 웃으며 미래를 계획하는 순간. 역광의 따뜻한 림라이트, 유리 난간 너머 보케 처리된 시티스카이라인, JB 브랜드 블루 소품 포인트"
  visual_mood: "생기, 낙관, 세련된 도시감성, 신뢰"
  color_palette: ["#0B2D6B", "#1F6BFF", "#FFD166", "#FFFFFF"]
  typography: "임팩트 있는 디스플레이 산세리프"
  aspect: "4:5"
material_matrix:
  - {channel: instagram, size: "1080x1350", aspect: "4:5"}
factsheet:
  product_name: "JB 20대 청년 정기예금"
  interest_rate: "연 2.80%"
  max_rate: "최고 연 3.30%"
  prime_rate: "우대 최대 연 0.50%p"
  term: "6~36개월"
  min_amount: "100만원"
  provider: "JB금융그룹"
disclosures:
  - "예금자보호법에 따라 5천만원까지 보호"
image_concept: "루프탑 카페 골든아워, 20대 커플, 역광 림라이트, 시티 보케, 브랜드 블루 포인트 소품, 좌측 절반 네거티브 스페이스"
---
# JB 20대 청년 정기예금 — 티키타카 검증
최고 연 3.30% 청년 우대. 첫 목돈의 시작을 JB와 함께.
"""


def main():
    port, cmd = sys.argv[1], sys.argv[2]
    base = f"http://127.0.0.1:{port}"
    if cmd == "new":
        run = json.loads(req("POST", f"{base}/runs", {"title": "tikitaka", "languages": ["ko"]}))["run_id"]
        req("PUT", f"{base}/vfs/{run}/brainstorming/plan.md", {"mime": "text/markdown", "content": PLAN})
        STATE.write_text(json.dumps({"run": run}), encoding="utf-8")
        print("run:", run)
        return
    run = json.loads(STATE.read_text(encoding="utf-8"))["run"]
    if cmd == "turn":
        prompt = sys.argv[3]
        action = sys.argv[4] if len(sys.argv) > 4 else None
        res = json.loads(req("POST", f"{base}/gateway/run", {
            "run_id": run, "studio": "design", "prompt": prompt,
            "provider": "google", "is_marker": True, "mock": True,
            "medium": "image", "action": action, "bypass_map": None}))
        meta = res.get("meta") or {}
        gate = meta.get("gate") or res.get("gate") or {}
        print("step:", meta.get("step"), "| gate:", json.dumps(gate, ensure_ascii=False)[:400])
        print("reply:", (res.get("text") or "")[:300])
    elif cmd == "preview":
        name = sys.argv[3]
        node = json.loads(req("GET", f"{base}/vfs/{run}/design/rough/preview.html"))
        html = node.get("content_text") or ""
        out = SP / f"tk_{name}.html"
        out.write_text(html, encoding="utf-8")
        print("saved:", out.name, "| bytes:", len(html), "| visual:", "data:image" in html)
    elif cmd == "spec":
        node = json.loads(req("GET", f"{base}/vfs/{run}/design/rough/layout.spec.json"))
        spec = json.loads(node.get("content_text") or "{}")
        slots = [(s.get("role"), s.get("bbox")) for s in spec.get("slots", []) if isinstance(s, dict)]
        print("aspect:", spec.get("aspect"), "| copy.ko:", json.dumps((spec.get("copy") or {}).get("ko", {}), ensure_ascii=False)[:300])
        print("slots:", json.dumps(slots, ensure_ascii=False))
    elif cmd == "poster":
        name = sys.argv[3]
        png = req("GET", f"{base}/vfs/{run}/design/design-system/components/visual/v1.png", raw=True)
        out = SP / f"tk_{name}.png"
        out.write_bytes(png)
        print("saved:", out.name, "| bytes:", len(png))


if __name__ == "__main__":
    main()
