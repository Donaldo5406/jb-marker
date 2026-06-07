import { describe, it, expect } from "vitest";
import { assembleScene, swapLanguage, aspectToDims } from "../sceneAssembler";

const SPEC = {
  aspect: "1:1",
  slots: [
    { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0,
      asset_ref: "design-system/components/visual/v1.png" },
    { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 200 }, z: 2, copy_key: "headline" },
  ],
  copy: { ko: { headline: "든든한 적금" }, en: { headline: "Solid Savings" } },
};

describe("assembleScene", () => {
  it("배경 슬롯은 image, 텍스트 슬롯은 textbox 객체로", () => {
    const scene = assembleScene(SPEC as any, "ko", (r) => `/vfs/r1/${r}`);
    const obj = scene.objects;
    expect(obj.find((o: any) => o.role === "background").type).toBe("image");
    const hl = obj.find((o: any) => o.role === "headline");
    expect(hl.type).toBe("textbox");
    expect(hl.text).toBe("든든한 적금");
    expect(hl.lang).toBe("ko");
  });

  it("bbox가 배열 [x,y,w,h]여도 좌표/크기를 숫자로 정규화한다 (demo_fixtures 호환)", () => {
    // demo_fixtures.py LAYOUT_SPEC은 bbox를 배열로 준다. 객체 접근(s.bbox.x)이면
    // 전부 undefined → 텍스트·이미지가 원점에 겹치고 이미지 scaleToWidth가 동작 안 함.
    const spec = {
      aspect: "1:1",
      slots: [
        { role: "background", bbox: [0, 0, 1080, 1080], z: 0,
          asset_ref: "design-system/components/visual/v1.png" },
        { role: "headline", bbox: [80, 120, 920, 300], z: 1, copy_key: "headline" },
      ],
      copy: { ko: { headline: "연 3.5% JB 정기예금" } },
    };
    const scene = assembleScene(spec as any, "ko", (r) => `/vfs/r1/${r}`);
    const bg = scene.objects.find((o: any) => o.role === "background");
    expect(bg.left).toBe(0);
    expect(bg.top).toBe(0);
    expect(bg.width).toBe(1080);   // FabricEditor.scaleToWidth(o.width)가 동작하려면 숫자여야 함
    const hl = scene.objects.find((o: any) => o.role === "headline");
    expect(hl.left).toBe(80);
    expect(hl.top).toBe(120);
    expect(hl.width).toBe(920);
  });

  it("bbox가 객체 {x,y,w,h}면 좌표를 그대로 숫자로 매핑한다", () => {
    const scene = assembleScene(SPEC as any, "ko", (r) => r);
    const hl = scene.objects.find((o: any) => o.role === "headline");
    expect(hl.left).toBe(80);
    expect(hl.top).toBe(120);
    expect(hl.width).toBe(920);
  });

  it("copy_key 없는 슬롯은 role을 키로 사용(disclosure 고지 렌더)", () => {
    const spec = {
      aspect: "1:1",
      slots: [
        { role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 60 }, z: 3 },
      ],
      copy: { ko: { disclosure: "본 이미지는 AI로 생성되었습니다." } },
    };
    const scene = assembleScene(spec as any, "ko", (r) => r);
    const disc = scene.objects.find((o: any) => o.role === "disclosure");
    expect(disc.type).toBe("textbox");
    expect(disc.text).toBe("본 이미지는 AI로 생성되었습니다.");
  });

  it("swapLanguage는 텍스트 객체 콘텐츠만 교체, 레이아웃 보존", () => {
    const ko = assembleScene(SPEC as any, "ko", (r) => r);
    const en = swapLanguage(ko, SPEC as any, "en");
    const koHl = ko.objects.find((o: any) => o.role === "headline");
    const enHl = en.objects.find((o: any) => o.role === "headline");
    expect(enHl.text).toBe("Solid Savings");
    expect(enHl.left).toBe(koHl.left);    // bbox 보존
    expect(enHl.lang).toBe("en");
  });

  it("aspect로 캔버스 width/height를 산출한다(4:5→1080×1350)", () => {
    const scene = assembleScene({ ...SPEC, aspect: "4:5" } as any, "ko", (r) => r);
    expect(scene.width).toBe(1080);
    expect(scene.height).toBe(1350);
  });
});

describe("aspectToDims", () => {
  it("W:H 비율로 높이를 산출(폭 1080 고정)", () => {
    expect(aspectToDims("4:5")).toEqual({ width: 1080, height: 1350 });
    expect(aspectToDims("1:1")).toEqual({ width: 1080, height: 1080 });
    expect(aspectToDims("16:9")).toEqual({ width: 1080, height: 608 });
  });
  it("미지정/이상값은 정사각 폴백", () => {
    expect(aspectToDims(undefined)).toEqual({ width: 1080, height: 1080 });
    expect(aspectToDims("abc")).toEqual({ width: 1080, height: 1080 });
    expect(aspectToDims("0:5")).toEqual({ width: 1080, height: 1080 });
  });
});
