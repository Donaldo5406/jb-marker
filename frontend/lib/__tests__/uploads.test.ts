import { describe, it, expect } from "vitest";
import {
  IMAGE_MAX, TEXT_MAX, UPLOAD_STUDIOS, readForPut, sanitizeFilename,
  uploadKind, uploadMime, uploadTargetPath, validateSize,
} from "@/lib/uploads";

describe("lib/uploads", () => {
  it("uploadKind — 확장자로 텍스트/이미지/거부 분류", () => {
    expect(uploadKind("a.md")).toBe("text");
    expect(uploadKind("b.CSV")).toBe("text");
    expect(uploadKind("c.png")).toBe("image");
    expect(uploadKind("d.JPG")).toBe("image");
    expect(uploadKind("e.exe")).toBeNull();
    expect(uploadKind("noext")).toBeNull();
  });
  it("sanitizeFilename — 경로/특수문자 무해화(한글 보존)", () => {
    expect(sanitizeFilename("논란 포스터(1).png")).toBe("논란_포스터_1_.png");
    expect(sanitizeFilename("../evil.md")).toBe(".._evil.md");
  });
  it("uploadTargetPath — {studio}/uploads/{파일명}", () => {
    expect(uploadTargetPath("review", "poster.png")).toBe("review/uploads/poster.png");
  });
  it("uploadMime — 확장자별 mime", () => {
    expect(uploadMime("a.json", "text")).toBe("application/json");
    expect(uploadMime("a.csv", "text")).toBe("text/csv");
    expect(uploadMime("a.md", "text")).toBe("text/markdown");
    expect(uploadMime("a.png", "image")).toBe("image/png");
    expect(uploadMime("a.jpg", "image")).toBe("image/jpeg");
  });
  it("validateSize — 캡 초과 시 에러 메시지", () => {
    expect(validateSize("text", TEXT_MAX + 1)).toMatch(/256KB/);
    expect(validateSize("image", IMAGE_MAX + 1)).toMatch(/5MB/);
    expect(validateSize("text", 10)).toBeNull();
  });
  it("readForPut — 텍스트는 원문, 이미지는 base64", async () => {
    const t = await readForPut(new File(["hello"], "a.md"), "text");
    expect(t).toEqual({ content: "hello" });
    const i = await readForPut(new File([new Uint8Array([1, 2, 3])], "a.png"), "image");
    expect(i.encoding).toBe("base64");
    expect(atob(i.content).length).toBe(3);
  });
  it("UPLOAD_STUDIOS — 소비자 있는 3개 스튜디오만", () => {
    expect([...UPLOAD_STUDIOS]).toEqual(["brainstorming", "design", "review"]);
  });
});
