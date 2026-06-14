import { describe, it, expect } from "vitest";
import {
  parseStoryboard, storyboardDuration, disclosureExposure, shotAt, activeLayers,
  DISCLOSURE_MIN_SEC, type Storyboard,
} from "../storyboard";

const SB: Storyboard = {
  fps: 30, bg_color: "#0B2B5B", duration_sec: 15, aspect: "9:16",
  shots: [
    { id: "s1", start: 0, end: 5, footage_prompt: "카페", layers: [
      { role: "headline", in: 0.5, out: 4, font_px: 96, color: "#fff", bbox: { x: 80, y: 300, w: 900, h: 220 } },
      { role: "disclosure", in: 1, out: 4, font_px: 36, bbox: { x: 80, y: 1700, w: 920, h: 120 } },
    ] },
    { id: "s2", start: 5, end: 15, layers: [
      { role: "cta", copy_key: "cta", in: 11, out: 14, bbox: { x: 80, y: 900, w: 900, h: 200 } },
      { role: "disclosure", in: 12, out: 14, bbox: { x: 80, y: 1700, w: 920, h: 120 } },
    ] },
  ],
  copy: { ko: { headline: "안녕", cta: "가입", disclosure: "예금자보호" }, en: { headline: "Hi" } },
};

describe("parseStoryboard", () => {
  it("유효 JSON을 파싱", () => { expect(parseStoryboard(JSON.stringify(SB))?.shots?.length).toBe(2); });
  it("깨진 JSON은 null", () => { expect(parseStoryboard("{broken")).toBeNull(); });
  it("비객체는 null", () => { expect(parseStoryboard("42")).toBeNull(); });
});

describe("storyboardDuration", () => {
  it("duration_sec 우선", () => { expect(storyboardDuration(SB)).toBe(15); });
  it("없으면 최대 end", () => { expect(storyboardDuration({ shots: [{ id: "a", start: 0, end: 8 }] })).toBe(8); });
});

describe("disclosureExposure", () => {
  it("disclosure 레이어 (out-in) 합산", () => { expect(disclosureExposure(SB)).toBe(5); });
  it("disclosure 없으면 0", () => { expect(disclosureExposure({ shots: [{ id: "a", start: 0, end: 3 }] })).toBe(0); });
});

describe("shotAt", () => {
  it("시간 구간의 샷", () => { expect(shotAt(SB, 6)?.id).toBe("s2"); });
  it("경계 밖이면 첫 샷 폴백", () => { expect(shotAt(SB, 99)?.id).toBe("s1"); });
});

describe("activeLayers", () => {
  it("time에 켜진 레이어만", () => {
    const a = activeLayers(SB, 2);
    expect(a.map((l) => l.role).sort()).toEqual(["disclosure", "headline"]);
  });
  it("어떤 레이어도 안 켜진 시각", () => { expect(activeLayers(SB, 4.5)).toEqual([]); });
});

describe("DISCLOSURE_MIN_SEC", () => { it("3.0", () => { expect(DISCLOSURE_MIN_SEC).toBe(3.0); }); });
