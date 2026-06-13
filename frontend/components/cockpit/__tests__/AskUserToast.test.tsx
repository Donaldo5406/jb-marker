import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AskUserToastView } from "../AskUserToast";

// 컨테이너(AskUserToast)는 useCockpit으로 pendingGate 봉투를 소비 — 기존 패턴(StudioNavToast.test) 답습.
// AskUserToastView 테스트는 useCockpit을 쓰지 않으므로 이 mock의 영향을 받지 않는다.
let ctx: any;
vi.mock("../CockpitProvider", () => ({ useCockpit: () => ctx }));
import { AskUserToast } from "../AskUserToast";

describe("AskUserToastView", () => {
  it("질문과 옵션을 렌더하고 선택 시 onSelect 호출", () => {
    const onSelect = vi.fn();
    render(<AskUserToastView ask={{ trigger: "b", question: "plan으로?", options: ["예", "아니오"] }}
            onSelect={onSelect} onClose={() => {}} />);
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
    fireEvent.click(screen.getByText("예"));
    expect(onSelect).toHaveBeenCalledWith("예");
  });

  it("ask가 null이면 아무것도 렌더하지 않음", () => {
    const { container } = render(<AskUserToastView ask={null} onSelect={() => {}} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("AskUserToast (컨테이너 — pendingGate 봉투 매핑, T1-P2 §4.4)", () => {
  it("kind=ask 봉투면 질문·옵션을 렌더하고 선택 시 answerAsk 호출", () => {
    const answerAsk = vi.fn();
    ctx = {
      pendingGate: { kind: "ask", actions: ["answer"], trigger: "b", question: "plan으로?", options: ["예", "아니오"] },
      answerAsk, closeAsk: vi.fn(),
    };
    render(<AskUserToast />);
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
    expect(screen.getByText("아니오")).toBeInTheDocument();
    fireEvent.click(screen.getByText("예"));
    expect(answerAsk).toHaveBeenCalledWith("예");
  });

  it("kind=status 봉투는 ask가 아니므로 렌더하지 않음", () => {
    ctx = { pendingGate: { kind: "status", actions: [], status: "PASS" }, answerAsk: vi.fn(), closeAsk: vi.fn() };
    const { container } = render(<AskUserToast />);
    expect(container.firstChild).toBeNull();
  });

  it("pendingGate=null이면 렌더하지 않음", () => {
    ctx = { pendingGate: null, answerAsk: vi.fn(), closeAsk: vi.fn() };
    const { container } = render(<AskUserToast />);
    expect(container.firstChild).toBeNull();
  });

  it("빈 trigger여도 question·options 있으면 렌더(기본 tone)", () => {
    ctx = {
      pendingGate: { kind: "ask", actions: ["answer"], trigger: "", question: "주력 채널?", options: ["카톡", "이메일"] },
      answerAsk: vi.fn(), closeAsk: vi.fn(),
    };
    render(<AskUserToast />);
    expect(screen.getByText("주력 채널?")).toBeInTheDocument();
    expect(screen.getByText("카톡")).toBeInTheDocument();
  });
});
