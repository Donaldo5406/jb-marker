import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../useFabricCanvas", () => ({ useFabricCanvas: () => ({ canvas: null }) }));
vi.mock("../../CockpitProvider", () => ({ useCockpit: () => ({ runId: "r1", designLang: "ko" }) }));

import { DesignEditor } from "../DesignEditor";

it("scene 내용이 깨졌을 때도 크래시 없이 툴바를 렌더", () => {
  render(<DesignEditor content="{broken" onSave={vi.fn()} onClose={vi.fn()} dirty={false} />);
  expect(screen.getByRole("button", { name: "scene 저장" })).toBeInTheDocument();
});
