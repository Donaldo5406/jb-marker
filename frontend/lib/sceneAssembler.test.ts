import { describe, it, expect } from "vitest";
import { assembleScene, type LayoutSpec } from "./sceneAssembler";

const spec: LayoutSpec = {
  aspect: "1:1",
  slots: [
    { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0, asset_ref: "v1.png" },
    { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 180 }, z: 3, copy_key: "headline",
      font_px: 96, color: "#0B1324" } as any,
    { role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 120 }, z: 1, copy_key: "disclosure",
      font_px: 30, color: "#FFFFFF" } as any,
  ],
  copy: { ko: { headline: "미래를 더 크게", disclosure: "예금자보호법에 따라 보호" } },
};

const url = (ref: string) => `https://cdn/${ref}`;

it("textbox가 layout.spec의 font_px를 반영(48 하드코딩 제거)", () => {
  const scene = assembleScene(spec, "ko", url);
  const headline = scene.objects.find((o) => o.role === "headline" && o.type === "textbox");
  expect(headline.fontSize).toBe(96);
  const disc = scene.objects.find((o) => o.role === "disclosure" && o.type === "textbox");
  expect(disc.fontSize).toBe(30);
});

it("각 textbox 슬롯마다 그보다 낮은 z의 스크림 rect가 삽입된다", () => {
  const scene = assembleScene(spec, "ko", url);
  const scrims = scene.objects.filter((o) => o.role === "scrim");
  expect(scrims.length).toBe(2); // headline, disclosure (background는 제외)
  // 스크림은 같은 슬롯 textbox보다 캔버스에서 먼저(아래) 그려진다
  const idxScrim = scene.objects.findIndex((o) => o.role === "scrim" && o.slotId === "headline");
  const idxText = scene.objects.findIndex((o) => o.type === "textbox" && o.role === "headline");
  expect(idxScrim).toBeLessThan(idxText);
});

it("밝은 글자(#FFFFFF)는 어두운 스크림, 어두운 글자(#0B1324)는 밝은 스크림", () => {
  const scene = assembleScene(spec, "ko", url);
  const discScrim = scene.objects.find((o) => o.role === "scrim" && o.slotId === "disclosure");
  expect(discScrim.fill).toBe("rgba(0,0,0,0.38)");       // 밝은 글자 → 어두운 스크림
  const headScrim = scene.objects.find((o) => o.role === "scrim" && o.slotId === "headline");
  expect(headScrim.fill).toBe("rgba(255,255,255,0.42)"); // 어두운 글자 → 밝은 스크림
});
