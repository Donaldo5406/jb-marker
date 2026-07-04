import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const sendChat = vi.fn().mockResolvedValue(undefined);
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
// ModelSelector 목: 실제 MODELS 순서(marker 최상단)를 재현 + onChange 트리거 버튼 노출.
vi.mock("../ModelSelector", () => {
  const MODELS = [
    { id: "marker", label: "Marker", provider: "anthropic", isMarker: true, paid: true },
    { id: "claude", label: "Claude", provider: "anthropic", isMarker: false },
  ];
  return {
    MODELS,
    ModelSelector: ({ value, onChange }: any) => (
      <button data-testid="pick-claude" data-value={value} onClick={() => onChange(MODELS[1])} />
    ),
  };
});

import { ChatPane } from "../ChatPane";

const base = {
  messages: [], brainStage: "A", videoMedium: "image", setVideoMedium: vi.fn(),
  sendChat, activeStudio: "design", chatPending: false, chatFocusNonce: 0,
};

async function typeAndSend(text: string) {
  fireEvent.change(screen.getByPlaceholderText(/메시지를 입력/), { target: { value: text } });
  fireEvent.keyDown(screen.getByPlaceholderText(/메시지를 입력/), { key: "Enter" });
  await waitFor(() => expect(sendChat).toHaveBeenCalled());
}

describe("ChatPane 모델 기본값·유지", () => {
  it("기본 모델은 Marker(Pro) — isMarker:true로 전송된다", async () => {
    ctx = { ...base };
    render(<ChatPane />);
    await typeAndSend("안녕");
    expect(sendChat).toHaveBeenLastCalledWith(
      expect.objectContaining({ isMarker: true, provider: "anthropic" }),
    );
  });

  it("선택한 모델은 재마운트(뷰 전환) 후에도 유지된다", async () => {
    ctx = { ...base };
    const first = render(<ChatPane />);
    fireEvent.click(screen.getByTestId("pick-claude")); // Claude로 변경
    first.unmount();                                     // 스튜디오 전환 = 재마운트
    render(<ChatPane />);
    expect(screen.getByTestId("pick-claude").dataset.value).toBe("claude");
  });
});
