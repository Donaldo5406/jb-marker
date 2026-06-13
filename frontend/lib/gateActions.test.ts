import { describe, it, expect } from "vitest";
import { gateActionLabel, GATE_ACTION_LABELS } from "./gateActions";

describe("gateActionLabel", () => {
  it("알려진 식별자는 한국어 라벨(6종 전부 회귀보호)", () => {
    expect(gateActionLabel("ack")).toBe("경고 확인 후 진행");
    expect(gateActionLabel("restart")).toBe("재검토");
    expect(gateActionLabel("regenerate")).toBe("재생성");
    expect(gateActionLabel("confirm")).toBe("확정 & 다음 →");
    expect(gateActionLabel("advance")).toBe("다음 단계 →");
    expect(gateActionLabel("answer")).toBe("답변");
  });
  it("미지 식별자는 식별자 자체를 라벨로", () => {
    expect(gateActionLabel("future_action")).toBe("future_action");
  });
  it("프론트 라벨 식별자 6종 정의(서버 envelope 5종 + 요청측 advance)", () => {
    expect(Object.keys(GATE_ACTION_LABELS).sort()).toEqual(
      ["ack", "advance", "answer", "confirm", "regenerate", "restart"]);
  });
});
