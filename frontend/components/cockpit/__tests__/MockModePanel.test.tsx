import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MockModePanelView } from "../MockModePanel";

describe("MockModePanelView", () => {
  it("on=true면 토글 aria-checked=true", () => {
    render(<MockModePanelView on={true} onToggle={() => {}} />);
    expect(screen.getByTestId("mock-toggle").getAttribute("aria-checked")).toBe("true");
  });

  it("클릭 시 onToggle 호출", () => {
    const onToggle = vi.fn();
    render(<MockModePanelView on={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByTestId("mock-toggle"));
    expect(onToggle).toHaveBeenCalled();
  });
});
