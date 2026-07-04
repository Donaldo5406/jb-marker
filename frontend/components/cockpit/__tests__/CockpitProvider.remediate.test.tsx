import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CockpitProvider, useCockpit } from "../CockpitProvider";

class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

// gateway 응답을 테스트가 주입. 그 외 엔드포인트(엔타이틀먼트·vfs·manifest)는 빈 객체.
let gatewayResponder: (body: any) => { ok: boolean; status: number; json: any };
// gateway/run 호출부 요청 바디를 캡처 — {studio, action} 계약 검증용.
let lastGatewayBody: any = null;

function jsonRes(status: number, obj: any) {
  return { ok: status >= 200 && status < 300, status, json: async () => obj };
}

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  lastGatewayBody = null;
  gatewayResponder = () => jsonRes(200, { text: "", meta: {}, gate: null }) as any;
  global.fetch = vi.fn(async (url: any, init?: any) => {
    const u = String(url);
    if (u.includes("/gateway/run")) {
      const body = init?.body ? JSON.parse(init.body) : {};
      lastGatewayBody = body;
      return gatewayResponder(body) as any;
    }
    return jsonRes(200, {}) as any; // entitlement/vfs/manifest 등 무해 빈응답
  }) as any;
});

function RemediateProbe() {
  const c = useCockpit();
  return (
    <div>
      <span data-testid="studio">{c.activeStudio}</span>
      <span data-testid="msgs">{c.messages.length}</span>
      <div data-testid="chat">{c.messages.map((m, i) => <p key={i}>{m.content}</p>)}</div>
      <button data-testid="remediate" onClick={() => void c.remediateFromReview()}>remediate</button>
    </div>
  );
}

/** Review 게이트 '리뷰 지적 반영해 재생성' 원클릭(폐루프 D4) — Design 전환 + remediate 액션 발사 +
 *  응답 text(적용한 권장수정 출처증빙)를 챗에 노출한다(리뷰 산출물이 소비됐다는 화면 증빙). */
describe("CockpitProvider — remediateFromReview(D4)", () => {
  it("remediateFromReview 호출 시 design 전환 + remediate 액션 + 증빙 챗 append", async () => {
    gatewayResponder = () => jsonRes(200, {
      text: "리뷰 권장수정 2건을 반영해 카피·고지를 교정했습니다: rec_aaaa1111(vi) · rec_bbbb2222(ko).",
      meta: { step: "done", remediated: true },
    }) as any;
    render(<CockpitProvider runId="r1"><RemediateProbe /></CockpitProvider>);
    // 초기 스튜디오는 brainstorming.
    expect(screen.getByTestId("studio").textContent).toBe("brainstorming");

    fireEvent.click(screen.getByTestId("remediate"));

    // 1) 활성 스튜디오가 design으로 전환.
    await waitFor(() => expect(screen.getByTestId("studio").textContent).toBe("design"));
    // 2) 응답 text가 messages에 assistant로 append(ChatPane 노출 계약).
    await waitFor(() => expect(screen.getByText(/리뷰 권장수정 2건/)).toBeTruthy());
    // 3) gateway/run이 {studio:"design", action:"remediate"}로 호출됨.
    expect(lastGatewayBody).toMatchObject({ studio: "design", action: "remediate" });
  });

  it("remediateFromReview 더블클릭 시 gatewayRun은 1회만 호출된다(재진입 가드, 중복 과금 방지)", async () => {
    let gatewayCalls = 0;
    gatewayResponder = () => {
      gatewayCalls += 1;
      return jsonRes(200, {
        text: "리뷰 권장수정을 반영해 카피·고지를 교정했습니다.",
        meta: { step: "done", remediated: true },
      }) as any;
    };
    render(<CockpitProvider runId="r1"><RemediateProbe /></CockpitProvider>);

    // 동일 틱에서 연타 — 첫 호출의 동기 구간(ref set)이 두 번째 호출을 즉시 막는지 검증.
    fireEvent.click(screen.getByTestId("remediate"));
    fireEvent.click(screen.getByTestId("remediate"));

    await waitFor(() => expect(screen.getByText(/리뷰 권장수정을 반영/)).toBeTruthy());
    expect(gatewayCalls).toBe(1);
  });
});
