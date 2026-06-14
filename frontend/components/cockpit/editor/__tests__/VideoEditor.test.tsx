import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("@/lib/useAuthedBlob", () => ({
  useAuthedBlob: () => ({ url: null, loading: false, error: false }),
}));

import { VideoEditor } from "../VideoEditor";

const SB = {
  duration_sec: 15, aspect: "9:16", bg_color: "#0B2B5B",
  shots: [
    { id: "s1", start: 0, end: 5, footage_prompt: "카페", camera: "handheld", layers: [
      { role: "headline", in: 0.5, out: 4, bbox: { x: 80, y: 300, w: 900, h: 220 }, font_px: 96 },
      { role: "disclosure", in: 1, out: 4, bbox: { x: 80, y: 1700, w: 920, h: 120 }, font_px: 36 },
    ] },
    { id: "s2", start: 5, end: 15, layers: [
      { role: "cta", in: 11, out: 14, bbox: { x: 80, y: 900, w: 900, h: 200 } },
      { role: "disclosure", in: 12, out: 14, bbox: { x: 80, y: 1700, w: 920, h: 120 } },
    ] },
  ],
  copy: { ko: { headline: "안녕하세요", cta: "가입하기", disclosure: "예금자보호" }, en: {} },
};
const content = JSON.stringify(SB);

function setup(over: Partial<React.ComponentProps<typeof VideoEditor>> = {}) {
  const onRender = vi.fn();
  const onSave = vi.fn();
  render(
    <VideoEditor
      content={content} runId="r1" lang="ko"
      rendering={false} onRender={onRender} onSave={onSave} {...over}
    />,
  );
  return { onRender, onSave };
}

describe("VideoEditor", () => {
  it("샷 트랙과 레이어 바를 렌더", () => {
    setup();
    expect(screen.getByTestId("video-shot-s1")).toBeInTheDocument();
    expect(screen.getByTestId("video-shot-s2")).toBeInTheDocument();
    expect(screen.getByTestId("video-layer-s1-0")).toBeInTheDocument();
  });

  it("고지 누적 노출 5.0초 → 미터에 표시 + 확정 활성", () => {
    setup();
    const meter = screen.getByTestId("disclosure-meter");
    expect(meter).toHaveTextContent("5");
    expect(screen.getByTestId("confirm-render")).not.toBeDisabled();
  });

  it("고지 <3초면 확정 비활성", () => {
    const short = { ...SB, shots: [{ id: "s1", start: 0, end: 5, layers: [
      { role: "disclosure", in: 1, out: 2 } ] }], copy: { ko: { disclosure: "x" }, en: {} } };
    render(<VideoEditor content={JSON.stringify(short)} runId="r1" lang="ko"
      rendering={false} onRender={vi.fn()} onSave={vi.fn()} />);
    expect(screen.getByTestId("confirm-render")).toBeDisabled();
  });

  it("확정 클릭 시 onRender 호출", () => {
    const { onRender } = setup();
    fireEvent.click(screen.getByTestId("confirm-render"));
    expect(onRender).toHaveBeenCalledTimes(1);
  });

  it("rendering=true면 확정 비활성 + 진행 라벨", () => {
    setup({ rendering: true });
    const btn = screen.getByTestId("confirm-render");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/렌더/);
  });

  it("레이어 선택 → 인스펙터에 카피·in/out 노출, 편집 후 저장 시 onSave", () => {
    const { onSave } = setup();
    fireEvent.click(screen.getByTestId("video-layer-s1-0"));
    const ta = screen.getByTestId("inspector-copy") as HTMLTextAreaElement;
    expect(ta.value).toBe("안녕하세요");
    fireEvent.change(ta, { target: { value: "변경" } });
    fireEvent.click(screen.getByTestId("save-storyboard"));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(JSON.parse(onSave.mock.calls[0][0]).copy.ko.headline).toBe("변경");
  });

  it("프리뷰 컨테이너 존재(렌더 안정성)", () => {
    setup();
    expect(screen.getByTestId("video-preview")).toBeInTheDocument();
  });

  it("깨진 content도 크래시 없이 안내", () => {
    render(<VideoEditor content="{broken" runId="r1" lang="ko"
      rendering={false} onRender={vi.fn()} onSave={vi.fn()} />);
    expect(screen.getByTestId("video-editor-empty")).toBeInTheDocument();
  });
});
