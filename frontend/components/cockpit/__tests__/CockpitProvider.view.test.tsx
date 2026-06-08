import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CockpitProvider, useCockpit, viewFromSearch } from "@/components/cockpit/CockpitProvider";

// CockpitProvider가 마운트 시 호출/임포트하는 모듈을 최소 스텁(네트워크·canvas 차단).
vi.mock("@/lib/api", () => ({
  api: { getEntitlement: vi.fn().mockResolvedValue({ marker: false }) },
  authedFetch: vi.fn(),
}));
vi.mock("@/lib/supabase", () => ({ ensureSession: vi.fn().mockResolvedValue(null) }));
vi.mock("@/lib/useRunSocket", () => ({ useRunSocket: vi.fn() }));
vi.mock("@/lib/sceneAssembler", () => ({ assembleScene: vi.fn() }));
vi.mock("@/lib/sceneRender", () => ({ renderAndUploadAll: vi.fn() }));

function ViewProbe() {
  const { view, setView } = useCockpit();
  return (
    <div>
      <span data-testid="view">{view}</span>
      <button onClick={() => setView("history")}>go-history</button>
      <button onClick={() => setView("workspace")}>go-workspace</button>
    </div>
  );
}

beforeEach(() => {
  window.history.replaceState(null, "", "/cockpit");
});

describe("viewFromSearch — 화이트리스트 정규화", () => {
  it("history/setting만 통과, 그 외/누락은 workspace", () => {
    expect(viewFromSearch("?view=history")).toBe("history");
    expect(viewFromSearch("?view=setting")).toBe("setting");
    expect(viewFromSearch("?view=bogus")).toBe("workspace");
    expect(viewFromSearch("")).toBe("workspace");
  });
});

describe("CockpitProvider ?view= 동기화", () => {
  it("/cockpit?view=history 진입 시 초기 view=history", async () => {
    window.history.replaceState(null, "", "/cockpit?view=history");
    render(
      <CockpitProvider>
        <ViewProbe />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("view").textContent).toBe("history"));
  });

  it("setView(history) → URL에 ?view=history, setView(workspace) → 쿼리 제거", async () => {
    render(
      <CockpitProvider>
        <ViewProbe />
      </CockpitProvider>,
    );
    fireEvent.click(screen.getByText("go-history"));
    await waitFor(() => expect(window.location.search).toContain("view=history"));
    fireEvent.click(screen.getByText("go-workspace"));
    await waitFor(() => expect(window.location.search).not.toContain("view"));
  });
});
