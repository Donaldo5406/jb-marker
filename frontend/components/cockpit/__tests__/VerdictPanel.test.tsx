import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictPanel } from "../review/VerdictPanel";

const base = {
  acknowledged: false,
  stage: "done",
  busy: false,
  onRun: vi.fn(),
  onAck: vi.fn(),
  onRestart: vi.fn(),
  onBackToDesign: vi.fn(),
  onProceedDeploy: vi.fn(),
};

describe("VerdictPanel effStatus (게이트 0/0 → PASS)", () => {
  it("critical·warning 0이면 백엔드 WARN이어도 PASS로 표시하고 ack 버튼을 숨긴다", () => {
    render(
      <VerdictPanel {...base} status="WARN" gate={{ critical: 0, warning: 0 }}
        actions={["ack", "regenerate", "restart"]} />,
    );
    expect(screen.getByText("PASS")).toBeTruthy();              // 배지 = effStatus
    expect(screen.queryByTestId("gate-action-ack")).toBeNull(); // '경고 확인 후 진행' 숨김
    expect(screen.getByText("위반 없음. 배포 진입 가능.")).toBeTruthy();
    expect(screen.getByTestId("gate-action-deploy")).toBeTruthy(); // PASS+done → Deploy 이동 버튼 노출
  });

  it("실제 WARN(warning>0)이면 PASS로 바꾸지 않고 ack 버튼을 노출한다", () => {
    render(
      <VerdictPanel {...base} status="WARN" gate={{ critical: 0, warning: 2 }}
        actions={["ack", "regenerate", "restart"]} />,
    );
    expect(screen.getByText("WARN")).toBeTruthy();
    expect(screen.getByTestId("gate-action-ack")).toBeTruthy();
  });

  it("BLOCKED(critical>0)은 그대로 BLOCKED이고 ack은 없다", () => {
    render(
      <VerdictPanel {...base} status="BLOCKED" gate={{ critical: 1, warning: 0 }}
        actions={["regenerate", "restart"]} />,
    );
    expect(screen.getByText("BLOCKED")).toBeTruthy();
    expect(screen.queryByTestId("gate-action-ack")).toBeNull();
    expect(screen.queryByTestId("gate-action-deploy")).toBeNull(); // BLOCKED엔 Deploy 이동 없음
  });
});
