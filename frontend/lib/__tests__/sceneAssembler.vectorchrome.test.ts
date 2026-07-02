import { describe, it, expect } from "vitest";
import { assembleScene } from "../sceneAssembler";

const VC = (slots: any[], copy: any = {}) => ({
  aspect: "4:5", render_mode: "vector_chrome",
  slots: [{ role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1350 }, z: 0, asset_ref: "v1.png" }, ...slots],
  copy: { ko: copy },
});

describe("vector_chrome: 텍스트 role 벡터 방출", () => {
  it("headline/body/cta를 textbox로 방출(baked와 달리)", () => {
    const spec = VC(
      [
        { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 180 }, z: 3, copy_key: "headline",
          font_px: 96, color: "#0B1324", font_family: "GmarketSansBold", weight: 800, align: "left" },
        { role: "cta", bbox: { x: 80, y: 900, w: 520, h: 96 }, z: 3, copy_key: "cta", color: "#FFFFFF" },
      ],
      { headline: "청춘의 저축", cta: "지금 가입하기" },
    );
    const s = assembleScene(spec as any, "ko", (r) => `/vfs/${r}`);
    const h = s.objects.find((o: any) => o.role === "headline");
    expect(h.type).toBe("textbox");
    expect(h.text).toBe("청춘의 저축");
    expect(h.fontFamily).toBe("GmarketSansBold");
    expect(h.fontWeight).toBe(800);
    expect(h.textAlign).toBe("left");
    expect(h.fill).toBe("#0B1324");
    expect(s.objects.find((o: any) => o.role === "cta").type).toBe("textbox");
  });

  it("font_family 미지정 텍스트는 DEFAULT_FONT(Pretendard) 폴백", () => {
    const spec = VC([{ role: "body", bbox: { x: 80, y: 340, w: 900, h: 120 }, z: 2, copy_key: "body" }],
      { body: "본문" });
    const s = assembleScene(spec as any, "ko", (r) => r);
    expect(s.objects.find((o: any) => o.role === "body").fontFamily).toBe("Pretendard");
  });

  it("baked 모드(render_mode 부재)는 headline을 방출하지 않는다(하위호환)", () => {
    const spec = { aspect: "4:5",
      slots: [{ role: "headline", bbox: { x: 80, y: 120, w: 920, h: 180 }, z: 3, copy_key: "headline" }],
      copy: { ko: { headline: "H" } } };
    const s = assembleScene(spec as any, "ko", (r) => r);
    expect(s.objects.some((o: any) => o.role === "headline")).toBe(false);
  });
});
