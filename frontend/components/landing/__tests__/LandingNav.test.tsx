import { describe, expect, it } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LandingNav } from "@/components/landing/LandingNav";

describe("LandingNav 와이어링", () => {
  it("죽은 앵커 '연동가능한 앱'(/#apps)이 없다", () => {
    const { container } = render(<LandingNav />);
    expect(container.querySelector('a[href="/#apps"]')).toBeNull();
    expect(screen.queryByText("연동가능한 앱")).toBeNull();
  });

  it("History 진입 링크(/cockpit?view=history · '작업 내역')가 있다", () => {
    const { container } = render(<LandingNav />);
    expect(container.querySelector('a[href="/cockpit?view=history"]')).not.toBeNull();
    expect(screen.getByText("작업 내역")).toBeTruthy();
  });

  it("결제·체험해보기 링크는 유지된다", () => {
    const { container } = render(<LandingNav />);
    expect(container.querySelector('a[href="/pricing"]')).not.toBeNull();
    expect(container.querySelector('a[href="/cockpit"]')).not.toBeNull();
  });

  it("파이프라인 소개 드롭다운 서브항목이 각 단계 앵커로 연결된다(hover)", async () => {
    const { container } = render(<LandingNav />);
    // 드롭다운은 hover 시에만 마운트된다 → 부모 래퍼에 mouseEnter.
    fireEvent.mouseEnter(screen.getByText("파이프라인 소개").closest("div")!);
    await waitFor(() => {
      expect(container.querySelector('a[href="/#step-planning"]')).not.toBeNull();
    });
    expect(container.querySelector('a[href="/#step-design"]')).not.toBeNull();
    expect(container.querySelector('a[href="/#step-review"]')).not.toBeNull();
  });
});
