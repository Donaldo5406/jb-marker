import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CockpitProvider, useCockpit, type CockpitContextValue } from "../CockpitProvider";
import { AskUserToast } from "../AskUserToast";

/** 게이트 봉투(T1-P2 §4.4) 소비 통합 테스트 — 실제 CockpitProvider + fetch mock.
 *  reviewActions.test.tsx(installFetch + Capture)·sceneWins.test.tsx(stateful store) 패턴 답습. */

class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

const ASK = { trigger: "b", question: "plan으로?", options: ["예", "아니오"] };

/** 서버 정본 시뮬: gateway가 ask 봉투를 내면 _state.json.pending_ask(구 dict)에도 기록 —
 *  sendChat 직후 loadBrainState가 서버 정본으로 수렴하는 실제 플로를 미러링한다. */
function installFetch(store: { pendingAsk: typeof ASK | null }) {
  const gatewayCalls: any[] = [];
  const fetchMock = vi.fn(async (input: any, init?: any) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(init.body) : undefined;
    const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });

    if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
    if (url.endsWith("/entitlement")) return ok({ marker: false });
    if (/\/vfs\/[^/]+$/.test(url) && method === "GET") return ok({ nodes: [] });
    if (url.includes("brainstorming/_messages.json") && method === "GET")
      return { ok: false, status: 404, json: async () => ({}) };
    // _state.json — pending_ask는 구 dict 형식(내부 상태). 복원 시 ask 봉투로 매핑돼야 함(§4.4).
    if (url.includes("brainstorming/_state.json") && method === "GET")
      return ok({
        path: url, mime: "application/json", source: null, meta: {},
        content_text: JSON.stringify(store.pendingAsk ? { stage: "B", pending_ask: store.pendingAsk } : { stage: "B" }),
      });
    if (url.includes("design/_state.json") && method === "GET")
      return { ok: false, status: 404, json: async () => ({}) };
    if (url.endsWith("/gateway/run") && method === "POST") {
      gatewayCalls.push(body);
      // design 1턴 — gate 봉투 없음(null) + 단계 전진. 떠 있는 ask 토스트를 닫으면 안 됨(M1).
      if (body?.studio === "design")
        return ok({ output_path: "", text: "S1 진행", gate: null, meta: { step: "S1" } });
      // brainstorming: answer 동봉(answerAsk) → ask 해소(gate:null), 아니면 ask 봉투 발행.
      if (body?.answer) {
        store.pendingAsk = null;
        return ok({ output_path: "", text: "확정했습니다", gate: null, meta: { stage: "C" } });
      }
      store.pendingAsk = { ...ASK };
      return ok({
        output_path: "", text: "확인이 필요합니다",
        gate: { kind: "ask", actions: ["answer"], ...ASK }, meta: { stage: "B" },
      });
    }
    return ok({});
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { gatewayCalls };
}

let captured: CockpitContextValue | null = null;
function Capture() {
  captured = useCockpit();
  return null;
}

describe("게이트 봉투 소비 (T1-P2 §4.4)", () => {
  beforeEach(() => {
    captured = null;
    vi.stubGlobal("WebSocket", NoopWS as unknown as typeof WebSocket);
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("sendChat: gate=ask 봉투 → 토스트 표시, answerAsk 후 gate=null → 해소", async () => {
    installFetch({ pendingAsk: null });
    render(
      <CockpitProvider>
        <Capture />
        <AskUserToast />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r-ask"); });
    expect(captured!.pendingGate).toBeNull();

    // 챗 응답에 ask 봉투 → pendingGate 설정 + 토스트 렌더
    await act(async () => {
      await captured!.sendChat({ prompt: "포스터 만들어줘", provider: "anthropic", isMarker: true });
    });
    expect(captured!.pendingGate?.kind).toBe("ask");
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
    expect(screen.getByText("예")).toBeInTheDocument();

    // 답변 → 후속 응답 gate=null → 토스트 해소
    await act(async () => { await captured!.answerAsk("예"); });
    expect(captured!.pendingGate).toBeNull();
    expect(screen.queryByText("plan으로?")).toBeNull();
  });

  it("loadBrainState 복원: _state.json pending_ask(구 dict) → ask 봉투 매핑 + 토스트 표시", async () => {
    installFetch({ pendingAsk: { ...ASK } });
    render(
      <CockpitProvider>
        <Capture />
        <AskUserToast />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r-restore"); });
    // 구 dict가 봉투로 매핑돼야 함(kind/actions 부여)
    expect(captured!.pendingGate).toEqual({
      kind: "ask", actions: ["answer"],
      trigger: "b", question: "plan으로?", options: ["예", "아니오"],
    });
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
  });

  it("runDesign: gate=null 응답이 떠 있는 brainstorming ask 토스트를 닫지 않음(M1)", async () => {
    installFetch({ pendingAsk: { ...ASK } });
    render(
      <CockpitProvider>
        <Capture />
        <AskUserToast />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("r-cross"); });
    expect(captured!.pendingGate?.kind).toBe("ask");

    // design 1턴(gate 봉투 없음) — 교차 오염으로 ask가 닫히면 안 됨
    await act(async () => { await captured!.runDesign("next"); });
    expect(captured!.designStep).toBe("S1");
    expect(captured!.pendingGate?.kind).toBe("ask");
    expect(screen.getByText("plan으로?")).toBeInTheDocument();
  });
});
