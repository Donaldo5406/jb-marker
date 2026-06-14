import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ViolationCard } from "../review/ViolationCard";
import { EquivalenceCard } from "../review/EquivalenceCard";
import { VerdictPanel } from "../review/VerdictPanel";

describe("ViolationCard", () => {
  it("심각도·인용 법조항·근거를 렌더", () => {
    render(<ViolationCard v={{ node: "legal", severity: "critical", evidence: "과장 표현", clause: "표시광고법 §3", location: { slot: "title" }, lang: "ko" }} />);
    expect(screen.getByText("치명")).toBeTruthy();
    expect(screen.getByText(/표시광고법 §3/)).toBeTruthy();
    expect(screen.getByText("과장 표현")).toBeTruthy();
  });
});
describe("EquivalenceCard", () => {
  it("필수고지 누락(kind)·언어를 렌더", () => {
    render(<EquivalenceCard v={{ node: "i18n", severity: "critical", evidence: "원금손실 고지 누락", kind: "missing_disclosure", lang: "vi" }} />);
    expect(screen.getByText("치명")).toBeTruthy();
    expect(screen.getByText(/필수고지 누락/)).toBeTruthy();
  });
});
describe("VerdictPanel", () => {
  it("WARN+미ack면 경고확인 버튼, 클릭 시 onAck", () => {
    const onAck = vi.fn();
    render(<VerdictPanel status="WARN" gate={{ critical: 0, warning: 2 }} actions={["ack", "regenerate", "restart"]} acknowledged={false} stage="done" onRun={() => {}} onAck={onAck} onRestart={() => {}} onBackToDesign={() => {}} onProceedDeploy={() => {}} />);
    fireEvent.click(screen.getByText(/경고 확인/));
    expect(onAck).toHaveBeenCalled();
  });
  it("BLOCKED면 Design 복귀 CTA, 클릭 시 onBackToDesign", () => {
    const back = vi.fn();
    render(<VerdictPanel status="BLOCKED" gate={{ critical: 1, warning: 0 }} actions={["regenerate", "restart"]} acknowledged={false} stage="done" onRun={() => {}} onAck={() => {}} onRestart={() => {}} onBackToDesign={back} onProceedDeploy={() => {}} />);
    fireEvent.click(screen.getByText(/Design으로/));
    expect(back).toHaveBeenCalled();
  });
});
