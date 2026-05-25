import { describe, it, expect } from "vitest";
import { assembleScene, swapLanguage } from "../sceneAssembler";

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
});
