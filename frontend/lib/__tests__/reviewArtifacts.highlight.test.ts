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
});
