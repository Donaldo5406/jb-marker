import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EligibilityPanel } from "../EligibilityPanel";

const CAL = Array.from({ length: 24 }, (_, h) => ({ hour: h, blocked: h >= 21 || h < 8 }));

const BREAKDOWN = [
  {
    policy: "infomatics", label: "§50 정보통신망법",
    citation: "https://www.law.go.kr/법령/정보통신망이용촉진및정보보호등에관한법률/제50조",
    count: 43,
    reasons: [
      { status: "BLOCKED_NO_CONSENT", label: "마케팅 동의 없음", count: 30 },
      { status: "BLOCKED_NIGHT", label: "야간 발송 제한", count: 13 },
    ],
  },
  {
    policy: "pipa", label: "§15·§16 개인정보보호법",
    citation: "https://www.law.go.kr/법령/개인정보보호법/제15조",
    count: 44,
    reasons: [
      { status: "BLOCKED_PURPOSE", label: "수집목적 외 이용", count: 26 },
      { status: "BLOCKED_RETENTION", label: "보유기간 초과", count: 18 },
    ],
  },
];

describe("EligibilityPanel — 정책별 사유 분해(T10-UI)", () => {
  it("§50·§15·§16 그룹과 사유칩·인용을 렌더한다", () => {
    render(
      <EligibilityPanel
        total={512}
        eligibleCount={425}
        excludedCount={87}
        calendar={CAL}
        breakdown={BREAKDOWN}
      />,
    );
    // 두 정책 그룹 모두 렌더
    expect(screen.getByTestId("breakdown-infomatics")).toBeInTheDocument();
    expect(screen.getByTestId("breakdown-pipa")).toBeInTheDocument();
    // 사유칩 텍스트
    expect(screen.getByText("마케팅 동의 없음")).toBeInTheDocument();
    expect(screen.getByText("수집목적 외 이용")).toBeInTheDocument();
    expect(screen.getByText("보유기간 초과")).toBeInTheDocument();
    // 법령 인용 링크(공식 law.go.kr)
    const links = screen.getAllByRole("link");
    expect(links.some((a) => a.getAttribute("href")?.includes("law.go.kr"))).toBe(true);
  });

  it("breakdown이 없으면 분해 섹션을 렌더하지 않는다", () => {
    render(
      <EligibilityPanel total={512} eligibleCount={512} excludedCount={0} calendar={CAL} />,
    );
    expect(screen.queryByTestId("eligibility-breakdown")).toBeNull();
  });
});
