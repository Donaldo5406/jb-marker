import { describe, it, expect } from "vitest";
import { addLang, parseEdited, EDITED_PATH } from "../editedLangs";

describe("editedLangs", () => {
  it("EDITED_PATH는 design/_edited.json", () => {
    expect(EDITED_PATH).toBe("design/_edited.json");
  });
  it("addLang: 중복 없이 추가", () => {
    expect(addLang(["ko"], "en")).toEqual(["ko", "en"]);
    expect(addLang(["ko"], "ko")).toEqual(["ko"]);
    expect(addLang([], "vi")).toEqual(["vi"]);
  });
  it("parseEdited: {langs:[...]} 파싱, 깨지면 빈 배열", () => {
    expect(parseEdited(JSON.stringify({ langs: ["ko", "en"] }))).toEqual(["ko", "en"]);
    expect(parseEdited("nope")).toEqual([]);
    expect(parseEdited("{}")).toEqual([]);
  });
});
