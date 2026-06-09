import { describe, it, expect, vi } from "vitest";
import { exportFilename, triggerPngDownload } from "../exportPng";

describe("exportPng", () => {
  it("exportFilename: 언어 코드로 파일명 생성 + 위험문자 제거", () => {
    expect(exportFilename("ko")).toBe("design-ko.png");
    expect(exportFilename("zh-CN")).toBe("design-zh-CN.png");
    expect(exportFilename("")).toBe("design-design.png");
    expect(exportFilename("../etc")).toBe("design-etc.png");
  });
  it("triggerPngDownload: <a download>를 만들어 클릭+정리", () => {
    const click = vi.fn();
    const anchor: any = {};
    const appendChild = vi.fn();
    const removeChild = vi.fn();
    anchor.click = click;
    const doc: any = { createElement: vi.fn(() => anchor), body: { appendChild, removeChild } };
    triggerPngDownload("data:image/png;base64,AAAA", "design-ko.png", doc);
    expect(doc.createElement).toHaveBeenCalledWith("a");
    expect(anchor.href).toBe("data:image/png;base64,AAAA");
    expect(anchor.download).toBe("design-ko.png");
    expect(appendChild).toHaveBeenCalledWith(anchor);
    expect(click).toHaveBeenCalled();
    expect(removeChild).toHaveBeenCalledWith(anchor);
  });
});
