import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ModelSelector, MODELS } from "../ModelSelector";

describe("ModelSelector", () => {
  it("Marker가 목록 최상단이고 유료 배지를 가진다", () => {
    expect(MODELS[0].id).toBe("marker");
    expect(MODELS[0].paid).toBe(true);
    render(<ModelSelector value="fake" onChange={() => {}} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/Marker/)).toBeInTheDocument();
  });

  it("선택 시 onChange 호출", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="fake" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText(/Claude/));
    expect(onChange).toHaveBeenCalled();
  });
});
