import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LayersPanel } from "../LayersPanel";

const objects = [
  { type: "image", role: "background", visible: true },
  { type: "textbox", role: "headline", text: "든든한 적금", visible: true },
];

it("레이어 행을 위→아래(headline 먼저)로 렌더", () => {
  render(<LayersPanel objects={objects} activeIndex={null} onSelect={() => {}} onToggleVisible={() => {}} onToggleLock={() => {}} onForward={() => {}} onBackward={() => {}} />);
  const items = screen.getAllByRole("button", { name: /레이어 선택/ });
  expect(items[0]).toHaveTextContent("든든한 적금");
});

it("가시성 토글 클릭 → 해당 index로 onToggleVisible", () => {
  const onToggleVisible = vi.fn();
  render(<LayersPanel objects={objects} activeIndex={null} onSelect={() => {}} onToggleVisible={onToggleVisible} onToggleLock={() => {}} onForward={() => {}} onBackward={() => {}} />);
  fireEvent.click(screen.getAllByRole("button", { name: /가시성/ })[0]);
  expect(onToggleVisible).toHaveBeenCalledWith(1); // 최상단=headline=index 1
});
