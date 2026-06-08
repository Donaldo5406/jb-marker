import { describe, it, expect } from "vitest";
import { toLayers } from "../layersModel";

describe("toLayers", () => {
  it("객체 배열 → 레이어 행(역순: 위 객체가 목록 맨 위)", () => {
    const rows = toLayers([
      { type: "image", role: "background", visible: true },
      { type: "textbox", role: "headline", text: "든든한 적금", visible: true },
    ]);
    // 캔버스 마지막(최상단) = 목록 첫 행
    expect(rows[0].role).toBe("headline");
    expect(rows[0].index).toBe(1);
    expect(rows[1].role).toBe("background");
    expect(rows[1].index).toBe(0);
  });
  it("label: textbox는 텍스트 일부, 그 외엔 role||type", () => {
    const rows = toLayers([
      { type: "textbox", role: "body", text: "연 4.5% 우대금리 적용됩니다 길게" },
      { type: "rect" },
    ]);
    const body = rows.find((r) => r.role === "body")!;
    expect(body.label.startsWith("연 4.5%")).toBe(true);
    const rect = rows.find((r) => r.type === "rect")!;
    expect(rect.label).toBe("rect");
  });
  it("visible 기본 true, evented:false → locked true", () => {
    const rows = toLayers([{ type: "textbox", visible: false, evented: false }]);
    expect(rows[0].visible).toBe(false);
    expect(rows[0].locked).toBe(true);
  });
});
