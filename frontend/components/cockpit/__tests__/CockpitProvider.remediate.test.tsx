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

// gateway/run 호출 바디를 전부 캡처 — {studio, action} 계약 검증용. 교정(remediate)은
// 이제 자동 재검토(restart→R0→R3)까지 이어지므로 review 호출이 뒤따른다.
let gatewayBodies: any[] = [];

function jsonRes(status: number, obj: any) {
  return { ok: status >= 200 && status < 300, status, json: async () => obj } as any;
}

/** 스튜디오별 gateway 응답: 교정(design/remediate)은 remediated:true, 재검토(review)는
 *  R3로 즉시 종단(runReview 루프가 1회에 끝나 호출수 폭증 방지). */
function respond(body: any) {
  if (body?.studio === "review") return jsonRes(200, { text: "", meta: { step: "R3" }, gate: { kind: "status", status: "PASS", critical: 0, warning: 0 } });
  if (body?.action === "remediate") return jsonRes(200, {
    text: "리뷰 권장수정 2건을 반영해 카피·고지를 교정했습니다: rec_aaaa1111(vi) · rec_bbbb2222(ko).",
    meta: { step: "done", remediated: true },
  });
  return jsonRes(200, { text: "", meta: {}, gate: null });
}

beforeEach(() => {
  (global as any).WebSocket = NoopWS as any;
  gatewayBodies = [];
  global.fetch = vi.fn(async (url: any, init?: any) => {
    const u = String(url);
    if (u.includes("/gateway/run")) {
      const body = init?.body ? JSON.parse(init.body) : {};
      gatewayBodies.push(body);
      return respond(body);
    }
    return jsonRes(200, {}); // entitlement/vfs/manifest 등 무해 빈응답
  }) as any;
});

function RemediateProbe() {
  const c = useCockpit();
  return (
    <div>
      <span data-testid="studio">{c.activeStudio}</span>
      <div data-testid="chat">{c.messages.map((m, i) => <p key={i}>{m.content}</p>)}</div>
      <button data-testid="remediate" onClick={() => void c.remediateFromReview()}>remediate</button>
    </div>
  );
}

const remediateCalls = () => gatewayBodies.filter((b) => b.studio === "design" && b.action === "remediate");

/** Review 게이트 '리뷰 지적 반영해 재생성' 원클릭(폐루프 D4) — Design 전환 + remediate 액션 발사 +
 *  증빙 챗 append + **교정 후 자동 재검토**(사용자가 '재검토'를 수동으로 누를 필요 없음). */
describe("CockpitProvider — remediateFromReview(D4) + 자동 재검토", () => {
  it("remediate 액션 발사 + 증빙 챗 + 자동 재검토(review) 이후 Review 스튜디오 착지", async () => {
    render(<CockpitProvider runId="r1"><RemediateProbe /></CockpitProvider>);
    expect(screen.getByTestId("studio").textContent).toBe("brainstorming");

    fireEvent.click(screen.getByTestId("remediate"));

    // 1) 응답 text가 messages에 assistant로 append(ChatPane 노출 계약).
    await waitFor(() => expect(screen.getByText(/리뷰 권장수정 2건/)).toBeTruthy());
    // 2) gateway/run이 {studio:"design", action:"remediate"}로 호출됨(정확히 1회).
    expect(remediateCalls()).toHaveLength(1);
    // 3) 교정 후 자동 재검토 — review 스튜디오 gateway 호출이 뒤따른다.
    await waitFor(() => expect(gatewayBodies.some((b) => b.studio === "review")).toBe(true));
    // 4) 최종 착지 스튜디오 = review(자동 재검토 결과를 사용자가 바로 본다).
    await waitFor(() => expect(screen.getByTestId("studio").textContent).toBe("review"));
  });

  it("더블클릭 시 remediate 액션은 1회만(재진입 가드 — 중복 image-edit 과금 방지)", async () => {
    render(<CockpitProvider runId="r1"><RemediateProbe /></CockpitProvider>);

    // 동일 틱 연타 — 첫 호출의 동기 구간(ref set)이 두 번째 호출을 즉시 막는지 검증.
    fireEvent.click(screen.getByTestId("remediate"));
    fireEvent.click(screen.getByTestId("remediate"));

    await waitFor(() => expect(screen.getByText(/리뷰 권장수정 2건/)).toBeTruthy());
    await waitFor(() => expect(gatewayBodies.some((b) => b.studio === "review")).toBe(true));
    // 자동 재검토가 여러 review 호출을 하더라도 교정(remediate) 자체는 정확히 1회.
    expect(remediateCalls()).toHaveLength(1);
  });
});
