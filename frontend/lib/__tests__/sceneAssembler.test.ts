import { describe, it, expect } from "vitest";
import { assembleScene, swapLanguage, aspectToDims } from "../sceneAssembler";

const SPEC = {
  aspect: "1:1",
  slots: [
    { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0,
      asset_ref: "design-system/components/visual/v1.png" },
    { role: "disclosure", bbox: { x: 80, y: 120, w: 920, h: 200 }, z: 2, copy_key: "disclosure" },
  ],
  copy: { ko: { disclosure: "예금자보호 5천만원" }, en: { disclosure: "Protected" } },
};

describe("assembleScene — logo_policy baked(poc_E): 고지 오버레이 미방출", () => {
  it("logo_policy='baked'면 disclosure 오버레이(textbox·scrim)를 얹지 않는다(이중 오버레이 방지)", () => {
    const baked = { ...SPEC, logo_policy: "baked" };
    const scene = assembleScene(baked as any, "ko", (r) => `/vfs/r1/${r}`);
    // 배경(baked 포스터)만 남고 disclosure 오버레이·스크림은 없어야 한다.
    expect(scene.objects.some((o: any) => o.role === "disclosure")).toBe(false);
    expect(scene.objects.some((o: any) => o.role === "scrim")).toBe(false);
    expect(scene.objects.find((o: any) => o.role === "background").type).toBe("image");
  });
  it("logo_policy 미설정(기본)이면 종전대로 disclosure 오버레이를 방출한다(회귀 가드)", () => {
    const scene = assembleScene(SPEC as any, "ko", (r) => `/vfs/r1/${r}`);
    expect(scene.objects.some((o: any) => o.role === "disclosure" && o.type === "textbox")).toBe(true);
  });
});

describe("assembleScene", () => {
  it("배경 슬롯은 image, 텍스트(disclosure) 슬롯은 textbox 객체로", () => {
    const scene = assembleScene(SPEC as any, "ko", (r) => `/vfs/r1/${r}`);
    const obj = scene.objects;
    expect(obj.find((o: any) => o.role === "background").type).toBe("image");
    const disc = obj.find((o: any) => o.role === "disclosure");
    expect(disc.type).toBe("textbox");
    expect(disc.text).toBe("예금자보호 5천만원");
    expect(disc.lang).toBe("ko");
  });

  it("bbox가 배열 [x,y,w,h]여도 좌표/크기를 숫자로 정규화한다 (demo_fixtures 호환)", () => {
    // demo_fixtures.py LAYOUT_SPEC은 bbox를 배열로 준다. 객체 접근(s.bbox.x)이면
    // 전부 undefined → 텍스트·이미지가 원점에 겹치고 이미지 scaleToWidth가 동작 안 함.
    const spec = {
      aspect: "1:1",
      slots: [
        { role: "background", bbox: [0, 0, 1080, 1080], z: 0,
          asset_ref: "design-system/components/visual/v1.png" },
        { role: "disclosure", bbox: [80, 120, 920, 300], z: 1, copy_key: "disclosure" },
      ],
      copy: { ko: { disclosure: "예금자보호법에 따라 보호됩니다." } },
    };
    const scene = assembleScene(spec as any, "ko", (r) => `/vfs/r1/${r}`);
    const bg = scene.objects.find((o: any) => o.role === "background");
    expect(bg.left).toBe(0);
    expect(bg.top).toBe(0);
    expect(bg.width).toBe(1080);   // FabricEditor.scaleToWidth(o.width)가 동작하려면 숫자여야 함
    const disc = scene.objects.find((o: any) => o.role === "disclosure");
    expect(disc.left).toBe(80);
    expect(disc.top).toBe(120);
    expect(disc.width).toBe(920);
  });

  it("bbox가 객체 {x,y,w,h}면 좌표를 그대로 숫자로 매핑한다", () => {
    const scene = assembleScene(SPEC as any, "ko", (r) => r);
    const disc = scene.objects.find((o: any) => o.role === "disclosure");
    expect(disc.left).toBe(80);
    expect(disc.top).toBe(120);
    expect(disc.width).toBe(920);
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

  it("aspect로 캔버스 width/height를 산출한다(4:5→1080×1350)", () => {
    const scene = assembleScene({ ...SPEC, aspect: "4:5" } as any, "ko", (r) => r);
    expect(scene.width).toBe(1080);
    expect(scene.height).toBe(1350);
  });

  // 하이브리드 렌더: font_px 위계 회복 + 텍스트 슬롯 스크림(복잡한 비주얼 위 가독성)
  // 원-레이어 구조에서 헤드라인/바디/CTA는 배경에 베이크되므로 disclosure만 textbox/scrim.
  const SCRIM_SPEC = {
    aspect: "1:1",
    slots: [
      { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0, asset_ref: "v1.png" },
      { role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 120 }, z: 1, copy_key: "disclosure",
        font_px: 30, color: "#FFFFFF" },
    ],
    copy: { ko: { disclosure: "예금자보호법에 따라 보호" } },
  };

  it("textbox가 layout.spec의 font_px를 반영(disclosure)", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.find((o: any) => o.role === "disclosure" && o.type === "textbox").fontSize).toBe(30);
  });

  it("disclosure textbox 슬롯에 그보다 낮은 z의 스크림 rect가 삽입된다", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.filter((o: any) => o.role === "scrim").length).toBe(1); // disclosure(background 제외)
    const idxScrim = scene.objects.findIndex((o: any) => o.role === "scrim" && o.slotId === "disclosure");
    const idxText = scene.objects.findIndex((o: any) => o.type === "textbox" && o.role === "disclosure");
    expect(idxScrim).toBeLessThan(idxText);   // 스크림이 textbox보다 먼저(아래) 그려짐
  });

  it("밝은 글자(#FFFFFF)는 어두운 스크림(disclosure)", () => {
    const scene = assembleScene(SCRIM_SPEC as any, "ko", (r) => `/vfs/${r}`);
    expect(scene.objects.find((o: any) => o.role === "scrim" && o.slotId === "disclosure").fill).toBe("rgba(0,0,0,0.38)");
  });
});

describe("assembleScene (원-레이어)", () => {
  const SPEC: any = {
    aspect: "4:5",
    visual_by_lang: { ko: "visual/v1.png", en: "visual/v1.en.png" },
    slots: [
      { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1350 }, z: 0, asset_ref: "visual/v1.png" },
      { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 180 }, z: 3, copy_key: "headline", font_px: 96 },
      { role: "cta", bbox: { x: 80, y: 980, w: 520, h: 96 }, z: 3, copy_key: "cta" },
      { role: "disclosure", bbox: { x: 80, y: 1180, w: 920, h: 120 }, z: 1, copy_key: "disclosure", color: "#3A3A3A" },
      { role: "logo", bbox: { x: 48, y: 48, w: 300, h: 96 }, z: 9, asset_ref: "logo/v1.png" },
    ],
    copy: { ko: { headline: "청년 적금", cta: "지금 신청", disclosure: "예금자보호 5천만원" },
            en: { headline: "Youth Savings", cta: "Apply", disclosure: "Protected" } },
  };

  it("headline·cta는 textbox/scrim을 방출하지 않는다(배경에 베이크)", () => {
    const s = assembleScene(SPEC, "ko", (r) => `/vfs/${r}`);
    expect(s.objects.some((o: any) => o.role === "headline")).toBe(false);
    expect(s.objects.some((o: any) => o.role === "cta")).toBe(false);
  });

  it("배경(풀 포스터)·로고 image + disclosure textbox만 방출", () => {
    const s = assembleScene(SPEC, "ko", (r) => `/vfs/${r}`);
    expect(s.objects.find((o: any) => o.role === "background").type).toBe("image");
    expect(s.objects.find((o: any) => o.role === "logo").type).toBe("image");
    const disc = s.objects.find((o: any) => o.role === "disclosure");
    expect(disc.type).toBe("textbox");
    expect(disc.text).toBe("예금자보호 5천만원");
  });

  it("visual_by_lang로 언어별 배경 asset_ref를 해석", () => {
    const en = assembleScene(SPEC, "en", (r) => `/vfs/${r}`);
    expect(en.objects.find((o: any) => o.role === "background").src).toBe("/vfs/visual/v1.en.png");
  });

  it("visual_by_lang 없으면 배경 슬롯 asset_ref 폴백", () => {
    const { visual_by_lang, ...noMap } = SPEC;
    const s = assembleScene(noMap, "ko", (r) => `/vfs/${r}`);
    expect(s.objects.find((o: any) => o.role === "background").src).toBe("/vfs/visual/v1.png");
  });

  it("swapLanguage는 베이크 배경 + disclosure를 언어별 교체(로고 불변)", () => {
    const ko = assembleScene(SPEC, "ko", (r) => `/vfs/${r}`);
    const en = swapLanguage(ko, SPEC, "en", (r) => `/vfs/${r}`);
    expect(en.objects.find((o: any) => o.role === "background").src).toBe("/vfs/visual/v1.en.png");
    expect(en.objects.find((o: any) => o.role === "disclosure").text).toBe("Protected");
    expect(en.objects.find((o: any) => o.role === "logo").src).toBe("/vfs/logo/v1.png");
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
