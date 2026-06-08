import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { CockpitProvider, useCockpit, type CockpitContextValue } from "../CockpitProvider";

class NoopWS { onopen=null; onmessage=null; onclose=null; onerror=null; close=vi.fn(); constructor(public url: string){} }
let captured: CockpitContextValue | null = null;
function Capture() { captured = useCockpit(); return null; }

type Rec = { url: string; method: string; body: any };
function installFetch(store: Record<string, string>): { reqs: Rec[] } {
  const reqs: Rec[] = [];
  const fetchMock = vi.fn(async (input: any, init?: any) => {
    const url = String(input); const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(init.body) : undefined;
    reqs.push({ url, method, body });
    const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });
    if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
    if (url.endsWith("/entitlement")) return ok({ marker: false });
    if (/\/vfs\/[^/]+$/.test(url) && method === "GET") return ok({ nodes: [] });
    // _edited.json read
    if (url.includes("design/_edited.json") && method === "GET") {
      if (store["_edited"] === undefined) return { ok: false, status: 404, json: async () => ({}) };
      return ok({ content_text: store["_edited"] });
    }
    // final/{lang}/main.scene read → 저장본 존재 시 반환
    const sceneMatch = url.match(/design\/final\/(\w+)\/main\.scene/);
    if (sceneMatch && method === "GET") {
      const key = `scene_${sceneMatch[1]}`;
      if (store[key] === undefined) return { ok: false, status: 404, json: async () => ({}) };
      return ok({ path: url, mime: "application/json", content_text: store[key] });
    }
    if (url.includes("design/rough/layout.spec.json") && method === "GET")
      return ok({ content_text: JSON.stringify({ aspect: "1:1", slots: [{ role: "headline", bbox: { x: 0, y: 0, w: 100, h: 40 }, copy_key: "headline" }], copy: { ko: { headline: "원본카피" }, en: { headline: "orig" } } }) });
    if (url.includes("brainstorming/") && method === "GET") return { ok: false, status: 404, json: async () => ({}) };
    if (url.includes("design/_state.json") && method === "GET") return { ok: false, status: 404, json: async () => ({}) };
    if (method === "PUT") {
      // 저장 반영(scene/_edited 쓰기를 store에 기록)
      const sm = url.match(/design\/final\/(\w+)\/main\.scene/);
      if (sm) store[`scene_${sm[1]}`] = body.content;
      if (url.includes("design/_edited.json")) store["_edited"] = body.content;
      return ok({ path: url, mime: body?.mime ?? null, content_text: body?.content ?? "" });
    }
    if (method === "GET") return ok({ path: url, mime: "application/json", content_text: "{}" });
    return ok({});
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { reqs };
}

beforeEach(() => { captured = null; vi.stubGlobal("WebSocket", NoopWS as unknown as typeof WebSocket); window.history.replaceState(null, "", "/"); });
afterEach(() => { vi.restoreAllMocks(); });

describe("scene-wins", () => {
  it("saveSceneJson은 _edited.json에 현재 designLang을 마킹한다", async () => {
    const store: Record<string, string> = {};
    const { reqs } = installFetch(store);
    render(<CockpitProvider><Capture /></CockpitProvider>);
    await act(async () => { await captured!.openRun("run1"); });
    // ko 씬을 연 상태로 가정하고 저장
    await act(async () => { await captured!.switchDesignLang("ko"); });
    // openFile을 ko scene으로 강제(switchDesignLang이 selectFile로 설정)
    await act(async () => { await captured!.saveSceneJson(JSON.stringify({ version: "6.0.0", objects: [] })); });
    const editedPut = reqs.find((r) => r.method === "PUT" && r.url.includes("design/_edited.json"));
    expect(editedPut, "_edited.json PUT 되어야").toBeTruthy();
    expect(JSON.parse(editedPut!.body.content).langs).toContain("ko");
  });

  it("switchDesignLang: 마킹된 언어는 재조립(PUT) 없이 저장본을 연다", async () => {
    const store: Record<string, string> = {
      "_edited": JSON.stringify({ langs: ["en"] }),
      "scene_en": JSON.stringify({ version: "6.0.0", objects: [{ type: "textbox", role: "headline", lang: "en", text: "수동수정본" }] }),
    };
    const { reqs } = installFetch(store);
    render(<CockpitProvider><Capture /></CockpitProvider>);
    await act(async () => { await captured!.openRun("run1"); });
    reqs.length = 0;
    await act(async () => { await captured!.switchDesignLang("en"); });
    // en은 마킹됨 → main.scene 재조립 PUT 없어야
    const scenePut = reqs.find((r) => r.method === "PUT" && r.url.includes("design/final/en/main.scene"));
    expect(scenePut, "마킹 언어는 재조립하지 않아야").toBeFalsy();
    expect(captured!.designLang).toBe("en");
  });
});
