import { describe, it, expect, vi } from "vitest";
import { parseDataUrl, sanitizeAssetName, assetRestPath, importImageAsset } from "../imageImport";

describe("parseDataUrl", () => {
  it("data URL → {mime, base64}", () => {
    expect(parseDataUrl("data:image/png;base64,QUFBQg==")).toEqual({ mime: "image/png", base64: "QUFBQg==" });
  });
  it("data URL이 아니면 null", () => {
    expect(parseDataUrl("https://x/y.png")).toBeNull();
    expect(parseDataUrl("")).toBeNull();
  });
});

describe("sanitizeAssetName", () => {
  it("공백/특수문자를 -로, 확장자 보존", () => {
    expect(sanitizeAssetName("Hero Image.png")).toBe("Hero-Image.png");
    expect(sanitizeAssetName("a/b\\c.jpg")).toBe("a-b-c.jpg");
  });
});

describe("assetRestPath", () => {
  it("design/final/{lang}/assets/{seq}-{safe}", () => {
    expect(assetRestPath("ko", "Hero Image.png", 2)).toBe("design/final/ko/assets/2-Hero-Image.png");
  });
});

describe("importImageAsset", () => {
  it("vfsPut(base64) 호출 + assetUrl src 반환", async () => {
    const vfsPut = vi.fn().mockResolvedValue({});
    const deps = { vfsPut, assetUrl: (rest: string) => `URL:${rest}` };
    const out = await importImageAsset(deps, "ko", "x.png", "data:image/png;base64,QUFBQg==", 0);
    expect(out).toEqual({ src: "URL:design/final/ko/assets/0-x.png", rest: "design/final/ko/assets/0-x.png" });
    expect(vfsPut).toHaveBeenCalledWith("design/final/ko/assets/0-x.png", "QUFBQg==", "image/png");
  });
  it("dataURL이 잘못되면 null + vfsPut 미호출", async () => {
    const vfsPut = vi.fn();
    const deps = { vfsPut, assetUrl: (r: string) => r };
    const out = await importImageAsset(deps, "ko", "x.png", "not-a-data-url", 0);
    expect(out).toBeNull();
    expect(vfsPut).not.toHaveBeenCalled();
  });
});
