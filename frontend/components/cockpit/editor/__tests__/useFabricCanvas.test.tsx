import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import * as React from "react";

const add = vi.fn();
const clear = vi.fn();
const renderAll = vi.fn();
const dispose = vi.fn();
vi.mock("fabric", () => ({
  Canvas: vi.fn().mockImplementation(() => ({
    add, clear, renderAll, dispose,
    sendObjectToBack: vi.fn(),
    toObject: vi.fn(() => ({ version: "6.0.0", objects: [] })),
    on: vi.fn(), off: vi.fn(),
  })),
  Textbox: vi.fn().mockImplementation((t: string, opts: any) => ({ kind: "textbox", text: t, ...opts })),
  Rect: vi.fn().mockImplementation((o: any) => ({ kind: "rect", ...o })),
  FabricImage: {
    fromURL: vi.fn(async () => ({ kind: "image", set: vi.fn(), scaleToWidth: vi.fn() })),
    fromObject: vi.fn(async (o: any) => ({ kind: "image", ...o, set: vi.fn(), scaleToWidth: vi.fn() })),
  },
  FabricObject: { ownDefaults: {} },
}));
vi.mock("@/lib/fabricDefaults", () => ({}));
vi.mock("@/lib/api", () => ({ authedFetch: vi.fn(async () => ({ ok: false })) }));

import { useFabricCanvas } from "../useFabricCanvas";
import { FabricImage, Textbox } from "fabric";
import { authedFetch } from "@/lib/api";
import { waitFor } from "@testing-library/react";

beforeEach(() => { add.mockClear(); clear.mockClear(); vi.mocked(Textbox).mockClear(); });

describe("useFabricCanvas", () => {
  it("scene의 textbox를 동기 add 한다", () => {
    const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
    // scene은 안정적(메모이즈된) 참조여야 한다 — 프로덕션은 useMemo([content])로 보장.
    // 매 렌더 새 객체를 넘기면 로드 완료(loadVersion) 리렌더가 로드 effect를 재실행시켜 루프가 된다.
    const scene = { version: "6.0.0", objects: [{ type: "textbox", text: "안녕", left: 10, top: 10, width: 100 }], width: 1080, height: 1080 };
    renderHook(() => useFabricCanvas(elRef, scene));
    expect(clear).toHaveBeenCalled();
    expect(add).toHaveBeenCalledTimes(1);  // textbox 1개
  });

  it("scene의 스크림 rect를 add 하고, 같은 slotId textbox보다 아래(낮은 인덱스)에 둔다", () => {
    const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
    // assembleScene이 내보내는 순서: [scrim rect(낮은 z), textbox]. slotId로 짝을 식별.
    const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
      { type: "rect", left: 8, top: 8, width: 120, height: 60, fill: "rgba(0,0,0,0.38)", rx: 8, ry: 8, role: "scrim", slotId: "headline" },
      { type: "textbox", text: "헤드라인", left: 20, top: 20, width: 100, role: "headline", slotId: "headline" },
    ] };
    renderHook(() => useFabricCanvas(elRef, scene));
    // add된 객체들(공유 mock) — 동기 루프에서 배열 순서대로 들어간다.
    const added = add.mock.calls.map((c) => c[0]);
    const rect = added.find((o: any) => o.kind === "rect" && o.slotId === "headline");
    const textbox = added.find((o: any) => o.kind === "textbox" && o.slotId === "headline");
    expect(rect).toBeTruthy();              // 스크림이 캔버스에 추가됐다(현재 코드에선 스킵→실패)
    expect(textbox).toBeTruthy();
    const rectIdx = added.indexOf(rect);
    const tbIdx = added.indexOf(textbox);
    expect(rectIdx).toBeLessThan(tbIdx);    // 스크림이 자기 textbox보다 아래(먼저 add)
    expect((rect as any).selectable).toBe(false);  // 보조 배경 — 비선택
  });

  it("원-레이어 씬(배경 image + 로고 image + disclosure scrim rect + disclosure textbox)을 모두 렌더한다", async () => {
    // 원-레이어 피벗: 헤드라인/CTA는 배경 포스터에 베이크됨. 캔버스가 받는 씬은
    // 배경 image(풀 포스터) + 로고 image 오버레이 + disclosure scrim(rect) + disclosure textbox.
    // 이미지 분기는 role(background/logo) 무관 공통 — 둘 다 add 돼야 한다.
    vi.mocked(authedFetch).mockResolvedValue({ ok: true, blob: async () => new Blob() } as any);
    const origCreate = URL.createObjectURL;
    (URL as any).createObjectURL = vi.fn(() => "blob:x");
    (URL as any).revokeObjectURL = vi.fn();
    try {
      const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
      const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
        // 배경: 헤드라인·CTA가 베이크된 풀 포스터(어셈블러 씬 → scaleX 없음, scaleToWidth 경로)
        { type: "image", assetPath: "/vfs/r/poster.png", left: 0, top: 0, width: 1080, role: "background" },
        // 로고 오버레이
        { type: "image", assetPath: "/vfs/r/logo.png", left: 40, top: 40, width: 200, role: "logo" },
        // disclosure 가독성 배경(scrim) — textbox보다 먼저(낮은 z), 비선택
        { type: "rect", left: 8, top: 980, width: 1064, height: 80, fill: "rgba(0,0,0,0.38)", rx: 8, ry: 8, role: "scrim", slotId: "disclosure" },
        // disclosure textbox
        { type: "textbox", text: "투자에 따른 손실 위험", left: 20, top: 990, width: 1040, role: "disclosure", slotId: "disclosure" },
      ] };
      renderHook(() => useFabricCanvas(elRef, scene));

      // 동기 분기: scrim rect + disclosure textbox 즉시 add
      const addedSync = add.mock.calls.map((c) => c[0]);
      const scrim = addedSync.find((o: any) => o.kind === "rect" && o.slotId === "disclosure");
      const disclosure = addedSync.find((o: any) => o.kind === "textbox" && o.slotId === "disclosure");
      expect(scrim).toBeTruthy();              // disclosure scrim(rect) 추가됨
      expect((scrim as any).selectable).toBe(false);  // 보조 배경 — 비선택
      expect(disclosure).toBeTruthy();         // disclosure textbox 추가됨
      expect(addedSync.indexOf(scrim)).toBeLessThan(addedSync.indexOf(disclosure)); // scrim이 아래

      // 비동기 분기: 배경 + 로고 image 둘 다 add (공통 image 분기가 두 role 모두 처리)
      await waitFor(() => {
        const imgs = add.mock.calls.map((c) => c[0]).filter((o: any) => o.kind === "image");
        expect(imgs.length).toBe(2);
      });
      const images = add.mock.calls.map((c) => c[0]).filter((o: any) => o.kind === "image");
      expect(images.some((o: any) => o.assetPath === "/vfs/r/poster.png")).toBe(true);  // 배경
      expect(images.some((o: any) => o.assetPath === "/vfs/r/logo.png")).toBe(true);    // 로고
    } finally {
      (URL as any).createObjectURL = origCreate;
      vi.mocked(authedFetch).mockResolvedValue({ ok: false } as any);
    }
  });

  it("에디터 저장 이미지(scaleX·filters)는 fromObject로 전체 복원한다 (P3 회귀 가드)", async () => {
    vi.mocked(authedFetch).mockResolvedValue({ ok: true, blob: async () => new Blob() } as any);
    const origCreate = URL.createObjectURL;
    (URL as any).createObjectURL = vi.fn(() => "blob:x");
    (URL as any).revokeObjectURL = vi.fn();
    try {
      const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
      const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
        { type: "image", assetPath: "/vfs/r/a.png", scaleX: 0.5, scaleY: 0.5, left: 0, top: 0,
          filters: [{ type: "Brightness", brightness: 0.2 }] },
      ] };
      renderHook(() => useFabricCanvas(elRef, scene));
      await waitFor(() => expect((FabricImage as any).fromObject).toHaveBeenCalled());
      const arg = (FabricImage as any).fromObject.mock.calls[0][0];
      expect(arg.filters).toEqual([{ type: "Brightness", brightness: 0.2 }]);
      expect(arg.src).toBe("blob:x");
    } finally {
      (URL as any).createObjectURL = origCreate;
    }
  });

  it("vector_chrome textbox의 fontFamily/fontWeight/textAlign를 있을 때만 전달한다", () => {
    const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
    // vector_chrome 씬: rich 필드 있음(rate_card 라인) + 없음(baked disclosure 스타일) 한 씬에 공존.
    const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
      { type: "textbox", text: "연 3.5%", left: 40, top: 40, width: 400, fontSize: 72,
        fontFamily: "GmarketSansBold", fontWeight: 800, textAlign: "left", role: "rate_card", slotId: "rate_card" },
      { type: "textbox", text: "예금자보호 고지", left: 20, top: 990, width: 1040, role: "disclosure", slotId: "disclosure" },
    ] };
    renderHook(() => useFabricCanvas(elRef, scene));
    // 생성자 두 번째 인자(옵션)를 직접 검사 — 존재/부재를 정확히 판별.
    const richOpts = vi.mocked(Textbox).mock.calls[0][1] as any;
    expect(richOpts.fontFamily).toBe("GmarketSansBold");
    expect(richOpts.fontWeight).toBe(800);
    expect(richOpts.textAlign).toBe("left");
    // baked disclosure(리치 필드 없음)는 해당 키 자체가 옵션에 없어야 한다(하위호환 — 구성 옵션 종전과 동일).
    const bakedOpts = vi.mocked(Textbox).mock.calls[1][1] as any;
    expect("fontFamily" in bakedOpts).toBe(false);
    expect("fontWeight" in bakedOpts).toBe(false);
    expect("textAlign" in bakedOpts).toBe(false);
  });

  it("스크림 rect는 비선택 유지, rate_card rect는 선택 가능 + opacity/shadow 전달", () => {
    const elRef = { current: document.createElement("canvas") } as React.RefObject<HTMLCanvasElement>;
    const scene = { version: "6.0.0", width: 1080, height: 1080, objects: [
      { type: "rect", left: 8, top: 8, width: 120, height: 60, fill: "rgba(0,0,0,0.38)", rx: 8, ry: 8, role: "scrim", slotId: "headline" },
      { type: "rect", left: 40, top: 40, width: 400, height: 220, fill: "#FFFFFF", rx: 16, ry: 16,
        opacity: 0.94, shadow: "rgba(0,0,0,0.18) 0px 8px 24px", role: "rate_card", slotId: "rate_card" },
    ] };
    renderHook(() => useFabricCanvas(elRef, scene));
    const added = add.mock.calls.map((c) => c[0]);
    const scrim = added.find((o: any) => o.kind === "rect" && o.role === "scrim");
    const rateCard = added.find((o: any) => o.kind === "rect" && o.role === "rate_card");
    expect(scrim).toBeTruthy();
    expect((scrim as any).selectable).toBe(false);   // 스크림: 종전대로 비선택
    expect((scrim as any).evented).toBe(false);
    expect(rateCard).toBeTruthy();
    expect((rateCard as any).selectable).not.toBe(false);  // rate_card: 편집 가능(강제 false 아님)
    expect((rateCard as any).evented).not.toBe(false);
    expect((rateCard as any).opacity).toBe(0.94);          // opacity 전달
    expect((rateCard as any).shadow).toBe("rgba(0,0,0,0.18) 0px 8px 24px");  // shadow 문자열 전달
  });
});
