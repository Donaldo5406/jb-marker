import { describe, it, expect } from "vitest";
import { extOf, fileType, isImagePath } from "@/lib/fileType";

describe("fileType", () => {
  it("extOf는 마지막 확장자를 소문자로", () => {
    expect(extOf("a/b/main.SCENE")).toBe("scene");
    expect(extOf("README")).toBe("");
  });
  it(".json은 json 언어 + 주황 배경", () => {
    const t = fileType("layout.spec.json");
    expect(t.lang).toBe("json");
    expect(t.bg).toContain("#f7e8dc");
  });
  it(".md는 markdown, .ts는 typescript", () => {
    expect(fileType("spec.md").lang).toBe("markdown");
    expect(fileType("api.ts").lang).toBe("typescript");
  });
  it("미지정 확장자는 기본(plaintext)", () => {
    expect(fileType("data.bin").lang).toBe("plaintext");
  });
  it("isImagePath는 래스터 이미지만 true(대소문자 무관)", () => {
    expect(isImagePath("design/visual/v1.png")).toBe(true);
    expect(isImagePath("photo.JPG")).toBe(true);
    expect(isImagePath("anim.webp")).toBe(true);
    expect(isImagePath("layout.spec.json")).toBe(false);
    expect(isImagePath("main.scene")).toBe(false);
    expect(isImagePath("report.md")).toBe(false);
  });
});
