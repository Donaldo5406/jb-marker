import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { GalleryMedia } from "@/components/cockpit/GalleryMedia";
import * as hook from "@/lib/useAuthedBlob";

describe("GalleryMedia", () => {
  it("url 로드되면 img 표시", async () => {
    vi.spyOn(hook, "useAuthedBlob").mockReturnValue({
      url: "blob:x", loading: false, error: false,
    });
    render(<GalleryMedia runId="r1" rest="design/v1.png" name="v1.png" />);
    await waitFor(() => {
      const img = screen.getByAltText("v1.png") as HTMLImageElement;
      expect(img.src).toContain("blob:x");
    });
  });

  it("error면 플레이스홀더 표시", () => {
    vi.spyOn(hook, "useAuthedBlob").mockReturnValue({
      url: null, loading: false, error: true,
    });
    render(<GalleryMedia runId="r1" rest="design/v1.png" name="v1.png" />);
    expect(screen.getByText(/불러오지 못/)).toBeTruthy();
  });
});
