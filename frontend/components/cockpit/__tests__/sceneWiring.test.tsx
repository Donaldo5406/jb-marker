import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import { CockpitProvider, useCockpit, type CockpitContextValue } from "../CockpitProvider";

/** WS는 테스트에서 불필요 — 연결 안 함(noop). */
class NoopWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}

/** 백엔드 layout.spec(슬롯/카피 포함) — assembleScene 입력.
 *  원-레이어(a746ddf): 헤드라인/바디/CTA는 배경 이미지에 베이크되어 scene 텍스트로 방출되지 않는다.
 *  scene에 textbox로 남는 언어별 카피는 disclosure뿐 → 언어 동등성(R2)은 disclosure로 검증한다. */
const LAYOUT_SPEC = {
  aspect: "1:1",
  slots: [
    { role: "background", bbox: { x: 0, y: 0, w: 1080, h: 1080 }, z: 0 },
    { role: "headline", bbox: { x: 80, y: 120, w: 920, h: 200 }, z: 2, copy_key: "headline" },
    { role: "disclosure", bbox: { x: 80, y: 980, w: 920, h: 60 }, z: 3, copy_key: "disclosure" },
  ],
  copy: {
    ko: { headline: "든든한 적금", disclosure: "예금자보호 ko" },
    en: { headline: "Solid Savings", disclosure: "Depositor Protection en" },
    vi: { headline: "Tiết kiệm vững", disclosure: "Bảo hiểm vi" },
    zh: { headline: "稳健储蓄", disclosure: "存款保护 zh" },
  },
};

type Recorded = { url: string; method: string; body: any };

function installFetch(): { puts: Recorded[] } {
  const puts: Recorded[] = [];
  const fetchMock = vi.fn(async (input: any, init?: any) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(init.body) : undefined;
    if (method === "PUT") puts.push({ url, method, body });

    const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });

    // listRuns / runs
    if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
    if (url.endsWith("/entitlement")) return ok({ marker: false });
    // vfs list
    if (/\/vfs\/[^/]+$/.test(url) && method === "GET") return ok({ nodes: [] });
    // layout.spec.json GET
    if (url.includes("design/rough/layout.spec.json") && method === "GET") {
      return ok({ path: url, mime: "application/json", source: null, meta: {},
        content_text: JSON.stringify(LAYOUT_SPEC) });
    }
    // design/_state.json GET → 미시작(404 흉내)
    if (url.includes("design/_state.json") && method === "GET") {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    // brain state GETs → 비어있음
    if (url.includes("brainstorming/") && method === "GET") {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    // PUT (vfsPut) → echo node
    if (method === "PUT") {
      return ok({ path: url, mime: body?.mime ?? null, source: null, meta: {},
        content_text: body?.content ?? "" });
    }
    // 그 외 vfsGet(main.scene 등) → assembleScene 결과를 그대로 반환할 필요는 없으므로 빈 콘텐츠.
    if (method === "GET") {
      return ok({ path: url, mime: "application/json", source: null, meta: {}, content_text: "{}" });
    }
    return ok({});
  });
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
  return { puts };
}

let captured: CockpitContextValue | null = null;
function Capture() {
  captured = useCockpit();
  return null;
}

describe("scene-assembly wiring (C1/I4)", () => {
  beforeEach(() => {
    captured = null;
    vi.stubGlobal("WebSocket", NoopWS as unknown as typeof WebSocket);
    // ?run= 없이 시작 — openRun을 명시적으로 호출.
    window.history.replaceState(null, "", "/");
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("switchDesignLang은 layout.spec를 읽어 final/{lang}/main.scene로 vfsPut 한다", async () => {
    const { puts } = installFetch();
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    // run 열기(상태 복원 경로) — 그래야 runIdRef가 채워짐.
    await act(async () => { await captured!.openRun("run1"); });
    // 언어 전환 → assembleAndOpenScene 트리거
    await act(async () => { await captured!.switchDesignLang("en"); });

    const scenePut = puts.find((p) => p.url.includes("design/final/en/main.scene"));
    expect(scenePut, "final/en/main.scene 로 PUT 되어야 함").toBeTruthy();
    // 조립된 scene이 valid한 Fabric JSON이고 언어별 텍스트(disclosure)가 영어 카피로 들어갔는지 확인.
    const scene = JSON.parse(scenePut!.body.content);
    expect(scene.version).toBe("6.0.0");
    // 원-레이어: 헤드라인은 배경에 베이크되어 scene 텍스트로 방출되지 않는다(회귀 가드).
    expect(scene.objects.find((o: any) => o.role === "headline")).toBeUndefined();
    const disc = scene.objects.find((o: any) => o.role === "disclosure");
    expect(disc.text).toBe("Depositor Protection en");
    expect(disc.lang).toBe("en");
    // 배경 슬롯은 고정 비주얼 경로로 연결.
    const bg = scene.objects.find((o: any) => o.role === "background");
    expect(bg.type).toBe("image");
    expect(bg.src).toContain("design-system/components/visual/v1.png");
    // designLang 상태도 전환됨.
    expect(captured!.designLang).toBe("en");
  });

  it("runDesign done은 plan 전체 언어의 final/{lang}/main.scene를 일괄 조립한다(R2 4언어)", async () => {
    const puts: Recorded[] = [];
    const LANGS = ["ko", "en", "vi", "zh"];
    const fetchMock = vi.fn(async (input: any, init?: any) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const body = init?.body ? JSON.parse(init.body) : undefined;
      if (method === "PUT") puts.push({ url, method, body });
      const ok = (json: any) => ({ ok: true, status: 200, json: async () => json });
      if (url.endsWith("/runs") && method === "GET") return ok({ runs: [] });
      if (url.endsWith("/entitlement")) return ok({ marker: false });
      // design 파이프라인 1턴 → done
      if (url.includes("/gateway/run") && method === "POST")
        return ok({ text: "디자인 확정", meta: { step: "done" } });
      if (/\/vfs\/[^/]+$/.test(url) && method === "GET") return ok({ nodes: [] });
      // _state.json → plan 언어 4개(정본)
      if (url.includes("design/_state.json") && method === "GET")
        return ok({ content_text: JSON.stringify({ languages: LANGS }) });
      if (url.includes("design/rough/layout.spec.json") && method === "GET")
        return ok({ content_text: JSON.stringify(LAYOUT_SPEC) });
      if (url.includes("brainstorming/") && method === "GET")
        return { ok: false, status: 404, json: async () => ({}) };
      if (method === "PUT")
        return ok({ path: url, mime: body?.mime ?? null, content_text: body?.content ?? "" });
      if (method === "GET")
        return ok({ path: url, mime: "application/json", content_text: "{}" });
      return ok({});
    });
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("run3"); });
    await act(async () => { await captured!.runDesign("advance"); });
    // 4언어 모두 main.scene PUT + 언어별로 올바른 카피/lang가 조립돼야 함(R2 동등성 입력).
    // 원-레이어: 헤드라인은 배경 베이크 → scene 텍스트는 disclosure로 언어 동등성을 검증.
    const EXPECT: Record<string, string> = {
      ko: "예금자보호 ko", en: "Depositor Protection en", vi: "Bảo hiểm vi", zh: "存款保护 zh",
    };
    const discTexts: string[] = [];
    for (const lang of LANGS) {
      const put = puts.find((p) => p.url.includes(`design/final/${lang}/main.scene`));
      expect(put, `final/${lang}/main.scene PUT 누락`).toBeTruthy();
      const scene = JSON.parse(put!.body.content);
      expect(scene.objects.find((o: any) => o.role === "headline"),
        `${lang} 헤드라인은 배경 베이크라 textbox로 방출되면 안 됨`).toBeUndefined();
      const disc = scene.objects.find((o: any) => o.role === "disclosure");
      expect(disc.lang, `${lang} disclosure.lang 불일치`).toBe(lang);
      expect(disc.text, `${lang} disclosure 카피 불일치`).toBe(EXPECT[lang]);
      discTexts.push(disc.text);
    }
    // 잘못된 단일 언어 일괄 조립(예: 전부 langs[0]) 회귀 가드 — 4개 텍스트가 모두 달라야 함.
    expect(new Set(discTexts).size).toBe(LANGS.length);
  });

  it("rough spec이 없으면 scene을 만들지 않는다(no-op)", async () => {
    const puts: Recorded[] = [];
    const fetchMock = vi.fn(async (input: any, init?: any) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "PUT") puts.push({ url, method, body: JSON.parse(init.body) });
      if (url.endsWith("/runs")) return { ok: true, status: 200, json: async () => ({ runs: [] }) };
      if (url.endsWith("/entitlement")) return { ok: true, status: 200, json: async () => ({ marker: false }) };
      if (/\/vfs\/[^/]+$/.test(url) && method === "GET")
        return { ok: true, status: 200, json: async () => ({ nodes: [] }) };
      // 모든 vfsGet은 404(rough spec 포함)
      return { ok: false, status: 404, json: async () => ({}) };
    });
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    render(
      <CockpitProvider>
        <Capture />
      </CockpitProvider>,
    );
    await act(async () => { await captured!.openRun("run2"); });
    await act(async () => { await captured!.switchDesignLang("vi"); });
    const scenePut = puts.find((p) => p.url.includes("main.scene"));
    expect(scenePut, "spec 없으면 PUT 하지 않아야 함").toBeFalsy();
    // 언어 상태는 그래도 전환.
    expect(captured!.designLang).toBe("vi");
  });
});
