import { describe, it, expect } from "vitest";
import { SCENE_CUSTOM_PROPS, parseScene } from "../sceneSerialize";

describe("SCENE_CUSTOM_PROPS", () => {
  it("Review/i18n가 의존하는 role·lang·slotID + filters를 포함한다", () => {
    expect(SCENE_CUSTOM_PROPS).toEqual(
      expect.arrayContaining(["role", "lang", "slotId", "filters"]),
    );
  });
});

describe("parseScene", () => {
  it("유효 JSON → objects 배열 보존", () => {
    const json = JSON.stringify({ version: "6.0.0", objects: [{ type: "textbox", role: "headline" }], width: 1080, height: 1080 });
    const s = parseScene(json);
    expect(s?.objects[0].role).toBe("headline");
    expect(s?.width).toBe(1080);
  });
  it("빈 문자열/깨진 JSON → null", () => {
    expect(parseScene("")).toBeNull();
    expect(parseScene("{not json")).toBeNull();
  });
  it("objects 누락 → 빈 배열로 정규화", () => {
    expect(parseScene("{}")?.objects).toEqual([]);
  });
});
