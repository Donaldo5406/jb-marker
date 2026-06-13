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

  // 하이브리드 렌더: font_px 위계 회복 + 텍스트 슬롯 스크림(복잡한 비주얼 위 가독성)
  const SCRIM_SPEC = {
    aspect: "1:1",
    slots: [
      { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0, asset_ref: "v1.png" },
      { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 180 }, z: 3, copy_key: "headline",
        font_px: 96, color: "#0B1324" },
      { role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 120 }, z: 1, copy_key: "disclosure",
        font_px: 30, color: "#FFFFFF" },
    ],
    copy: { ko: { headline: "미래를 더 크게", disclosure: "예금자보호법에 따라 보호" } },
  };

  it("textbox가 layout.spec의 font_px를 반영(48 하드코딩 제거)", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.find((o: any) => o.role === "headline" && o.type === "textbox").fontSize).toBe(96);
    expect(scene.objects.find((o: any) => o.role === "disclosure" && o.type === "textbox").fontSize).toBe(30);
  });

  it("각 textbox 슬롯마다 그보다 낮은 z의 스크림 rect가 삽입된다", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.filter((o: any) => o.role === "scrim").length).toBe(2); // headline·disclosure(background 제외)
    const idxScrim = scene.objects.findIndex((o: any) => o.role === "scrim" && o.slotId === "headline");
    const idxText = scene.objects.findIndex((o: any) => o.type === "textbox" && o.role === "headline");
    expect(idxScrim).toBeLessThan(idxText);   // 스크림이 textbox보다 먼저(아래) 그려짐
  });

  it("밝은 글자(#FFFFFF)는 어두운 스크림, 어두운 글자(#0B1324)는 밝은 스크림", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.find((o: any) => o.role === "scrim" && o.slotId === "disclosure").fill).toBe("rgba(0,0,0,0.38)");
    expect(scene.objects.find((o: any) => o.role === "scrim" && o.slotId === "headline").fill).toBe("rgba(255,255,255,0.42)");
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
