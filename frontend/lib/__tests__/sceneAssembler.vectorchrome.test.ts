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

describe("vector_chrome: disclosure fontFamily 게이트(byte-equivalence)", () => {
  const discSpec = (renderMode?: string) => ({
    aspect: "1:1", ...(renderMode ? { render_mode: renderMode } : {}),
    slots: [{ role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 60 }, z: 3, copy_key: "disclosure" }],
    copy: { ko: { disclosure: "예금자보호 5천만원" } },
  });
  it("baked 모드(render_mode 부재)는 disclosure textbox에 fontFamily가 없다(현행 불변)", () => {
    const s = assembleScene(discSpec() as any, "ko", (r) => r);
    const disc = s.objects.find((o: any) => o.role === "disclosure" && o.type === "textbox");
    expect("fontFamily" in disc).toBe(false);
  });
  it("vector_chrome 모드는 disclosure textbox에 fontFamily(Pretendard 폴백)를 적용", () => {
    const s = assembleScene(discSpec("vector_chrome") as any, "ko", (r) => r);
    const disc = s.objects.find((o: any) => o.role === "disclosure" && o.type === "textbox");
    expect(disc.fontFamily).toBe("Pretendard");
  });
});

describe("vector_chrome: rate_card", () => {
  it("컨테이너 rect + line별 textbox(style→크기/굵기)", () => {
    const spec = {
      aspect: "4:5", render_mode: "vector_chrome",
      slots: [
        { role: "rate_card", bbox: { x: 80, y: 700, w: 920, h: 260 }, z: 2,
          container: { fill: "#FFFFFF", radius: 16, opacity: 0.94, shadow: true },
          lines: [
            { text: "최고 연", style: "label" },
            { text: "3.30%", style: "figure" },
            { text: "기본 2.80% · 우대 0.50%p", style: "caption" },
          ] },
      ],
      copy: { ko: {} },
    };
    const s = assembleScene(spec as any, "ko", (r) => r);
    const rect = s.objects.find((o: any) => o.role === "rate_card" && o.type === "rect");
    expect(rect.fill).toBe("#FFFFFF");
    expect(rect.rx).toBe(16);
    const figure = s.objects.find((o: any) => o.type === "textbox" && o.text === "3.30%");
    expect(figure.fontSize).toBe(72);
    expect(figure.fontWeight).toBe(800);
    const label = s.objects.find((o: any) => o.type === "textbox" && o.text === "최고 연");
    expect(label.fontSize).toBe(28);
    // 라인은 위→아래로 top 증가
    expect(label.top).toBeLessThan(figure.top);
  });
});

describe("vector_chrome: benefit_row", () => {
  it("item당 아이콘 image + title/desc textbox, 가로 균등 분배", () => {
    const spec = {
      aspect: "4:5", render_mode: "vector_chrome",
      slots: [
        { role: "benefit_row", bbox: { x: 80, y: 1000, w: 900, h: 140 }, z: 2,
          items: [
            { icon_key: "trending-up", title: "우대금리", desc: "최대 0.50%p" },
            { icon_key: "calendar", title: "가입기간", desc: "6~36개월" },
            { icon_key: "coins", title: "최소금액", desc: "100만원부터" },
          ] },
      ],
      copy: { ko: {} },
    };
    const s = assembleScene(spec as any, "ko", (r) => r);
    const icons = s.objects.filter((o: any) => o.role === "benefit_row" && o.type === "image");
    expect(icons.length).toBe(3);
    expect(icons[0].src).toBe("/icons/trending-up.svg");
    const titles = s.objects.filter((o: any) => o.type === "textbox" && ["우대금리", "가입기간", "최소금액"].includes(o.text));
    expect(titles.length).toBe(3);
    // 칼럼 균등: 두 번째 아이콘 left > 첫 번째
    expect(icons[1].left).toBeGreaterThan(icons[0].left);
    // 칼럼폭 = 900/3 = 300, 첫 칼럼 아이콘은 첫 칼럼 범위 내
    expect(icons[0].left).toBeGreaterThanOrEqual(80);
    expect(icons[0].left).toBeLessThan(80 + 300);
  });
});

describe("vector_chrome: cta_button", () => {
  it("둥근 rect + 중앙 텍스트(text_color)", () => {
    const spec = {
      aspect: "4:5", render_mode: "vector_chrome",
      slots: [
        { role: "cta_button", bbox: { x: 80, y: 1180, w: 520, h: 96 }, z: 3,
          fill: "#0066FF", text_color: "#FFFFFF", radius: 999, copy_key: "cta" },
      ],
      copy: { ko: { cta: "지금 가입하기" } },
    };
    const s = assembleScene(spec as any, "ko", (r) => r);
    const rect = s.objects.find((o: any) => o.role === "cta_button" && o.type === "rect");
    expect(rect.fill).toBe("#0066FF");
    expect(rect.rx).toBe(999);
    const txt = s.objects.find((o: any) => o.role === "cta_button" && o.type === "textbox");
    expect(txt.text).toBe("지금 가입하기");
    expect(txt.fill).toBe("#FFFFFF");
    expect(txt.textAlign).toBe("center");
  });
});
