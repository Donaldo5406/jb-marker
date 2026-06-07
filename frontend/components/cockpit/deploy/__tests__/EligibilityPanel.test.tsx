import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EligibilityPanel } from "../EligibilityPanel";

const CAL = Array.from({ length: 24 }, (_, h) => ({ hour: h, blocked: h >= 21 || h < 8 }));

// citation은 백엔드 정책 yaml의 매핑 형태 그대로(문자열 아님 — 실제 응답 형태와 일치).
const BREAKDOWN = [
  {
    policy: "infomatics", label: "§50 정보통신망법",
    citation: {
      law: "정보통신망 이용촉진 및 정보보호 등에 관한 법률", article: "제50조",
      source_url: "https://www.law.go.kr",
      quote: "오후 9시~익일 오전 8시 전송은 별도 사전 동의 필요; 수신거부 즉시 반영",
    },
    count: 43,
    reasons: [
      { status: "BLOCKED_NO_CONSENT", label: "마케팅 동의 없음", count: 30 },
      { status: "BLOCKED_NIGHT", label: "야간 발송 제한", count: 13 },
    ],
  },
  {
    policy: "pipa", label: "§15·§16 개인정보보호법",
    citation: {
      law: "개인정보 보호법", article: "제15조 · 제16조",
      source_url: "https://www.law.go.kr",
      quote: "수집 시 고지한 목적 외 이용 금지(§15) · 보유기간 준수(§16)",
    },
    count: 44,
    reasons: [
      { status: "BLOCKED_PURPOSE", label: "수집목적 외 이용", count: 26 },
      { status: "BLOCKED_RETENTION", label: "보유기간 초과", count: 18 },
    ],
  },
];

describe("EligibilityPanel — 정책별 사유 분해(T10-UI)", () => {
  it("§50·§15·§16 그룹과 사유칩·인용(객체 citation)을 렌더한다", () => {
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
    // 법령 인용: source_url로 href, law+article로 텍스트(객체 렌더 — 크래시 회귀 가드)
    const links = screen.getAllByRole("link");
    const lawLink = links.find((a) => a.getAttribute("href") === "https://www.law.go.kr");
    expect(lawLink).toBeTruthy();
    expect(lawLink!.textContent).toContain("제50조");
    // quote 본문도 렌더
    expect(screen.getByText(/수신거부 즉시 반영/)).toBeInTheDocument();
  });

  it("breakdown이 없으면 분해 섹션을 렌더하지 않는다", () => {
    render(
      <EligibilityPanel total={512} eligibleCount={512} excludedCount={0} calendar={CAL} />,
    );
    expect(screen.queryByTestId("eligibility-breakdown")).toBeNull();
  });
});
