import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import ArchitecturePage from "@/app/architecture/page";

describe("동작 원리 페이지", () => {
  it("랜딩 네비와 3개 섹션 앵커(#flow·#agent·#stack)가 있다", () => {
    const { container } = render(<ArchitecturePage />);
    // 랜딩 헤더 공유(공유 레이아웃이 없어 직접 렌더)
    expect(container.querySelector('a[href="/cockpit"]')).not.toBeNull();
    // 네비 드롭다운·앵커 딥링크 대상 섹션
    expect(container.querySelector("section#flow")).not.toBeNull();
    expect(container.querySelector("section#agent")).not.toBeNull();
    expect(container.querySelector("section#stack")).not.toBeNull();
  });
});
