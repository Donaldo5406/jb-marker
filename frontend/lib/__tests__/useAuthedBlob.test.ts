import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useAuthedBlob } from "@/lib/useAuthedBlob";
import * as apimod from "@/lib/api";

beforeEach(() => {
  (globalThis.URL as any).createObjectURL = vi.fn(() => "blob:fake-1");
  (globalThis.URL as any).revokeObjectURL = vi.fn();
});
afterEach(() => vi.restoreAllMocks());

describe("useAuthedBlob", () => {
  it("authedFetch 성공 시 objectURL을 반환", async () => {
    vi.spyOn(apimod, "authedFetch").mockResolvedValue(
      new Response(new Blob(["x"]), { status: 200 }),
    );
    const { result } = renderHook(() => useAuthedBlob("r1", "design/x.png"));
    await waitFor(() => expect(result.current.url).toBe("blob:fake-1"));
    expect(result.current.error).toBe(false);
  });

  it("실패 시 error=true", async () => {
    vi.spyOn(apimod, "authedFetch").mockResolvedValue(
      new Response("no", { status: 404 }),
    );
    const { result } = renderHook(() => useAuthedBlob("r1", "design/x.png"));
    await waitFor(() => expect(result.current.error).toBe(true));
    expect(result.current.url).toBe(null);
  });

  it("runId/rest가 null이면 fetch 안 함", () => {
    const spy = vi.spyOn(apimod, "authedFetch");
    const { result } = renderHook(() => useAuthedBlob(null, null));
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.url).toBe(null);
  });

  it("언마운트 시 revokeObjectURL 호출", async () => {
    vi.spyOn(apimod, "authedFetch").mockResolvedValue(
      new Response(new Blob(["x"]), { status: 200 }),
    );
    const { result, unmount } = renderHook(() => useAuthedBlob("r1", "design/x.png"));
    await waitFor(() => expect(result.current.url).toBe("blob:fake-1"));
    unmount();
    expect((globalThis.URL as any).revokeObjectURL).toHaveBeenCalledWith("blob:fake-1");
  });
});
