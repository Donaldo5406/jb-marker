import { describe, it, expect } from "vitest";
import { highlightImages, numberedForImage } from "@/lib/reviewArtifacts";
import type { ReviewVerdict } from "@/lib/reviewArtifacts";

const V = (id: string, sev: "critical" | "warning", image?: string, bbox?: boolean): ReviewVerdict => ({
  verdict_id: id, node: "legal", severity: sev,
  location: { image, ...(bbox ? { bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.1 } } : {}) },
});

describe("highlight helpers", () => {
  it("collects images that have bbox verdicts, in order", () => {
    const vs = [V("a", "warning", "p.png", true), V("b", "warning", "p.png", false), V("c", "critical", "q.png", true)];
    expect(highlightImages(vs)).toEqual(["p.png", "q.png"]);
  });
  it("numbers by critical-first then verdict_id, only bbox verdicts of that image", () => {
    const vs = [V("z", "critical", "p.png", true), V("a", "critical", "p.png", true), V("m", "warning", "p.png", true), V("x", "warning", "q.png", true)];
    const map = numberedForImage(vs, "p.png");
    expect(map.get("a")).toBe(1);
    expect(map.get("z")).toBe(2);
    expect(map.get("m")).toBe(3);
    expect(map.has("x")).toBe(false);
  });

  it("orders realistic legal/i18n verdict_ids: critical first, then verdict_id codepoint-ascending (백엔드 pin_sort_key 계약 동일성)", () => {
    // 실제 verdict_id 형태: legal_<8hex>_<slot>_<lang> / i18n_<8hex>_<slot>_<lang>
    const vs = [
      V("i18n_1b2c3d4e_disclosure_vi", "warning", "p.png", true),
      V("legal_0f3a9c21_headline_ko", "critical", "p.png", true),
      V("legal_0a1b2c3d_body_ko", "critical", "p.png", true),
      V("i18n_2a4f8b10_cta_th", "warning", "p.png", true),
      V("legal_9f0e1d2c_footer_ko", "warning", "q.png", true), // 다른 image — 매핑에서 제외돼야 함
    ];
    const map = numberedForImage(vs, "p.png");
    const byPin = [...map.entries()].sort((a, b) => a[1] - b[1]).map(([id]) => id);
    // critical 두 건이 먼저(코드포인트 순 'legal_0a...' < 'legal_0f...'), 그 다음 warning 두 건(코드포인트 순)
    expect(byPin).toEqual([
      "legal_0a1b2c3d_body_ko",
      "legal_0f3a9c21_headline_ko",
      "i18n_1b2c3d4e_disclosure_vi",
      "i18n_2a4f8b10_cta_th",
    ]);
    expect(map.has("legal_9f0e1d2c_footer_ko")).toBe(false);
  });
});
