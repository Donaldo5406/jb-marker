export type NewObjectKind = "textbox" | "rect" | "circle" | "line";
export type ObjectSpec = { ctor: NewObjectKind; props: Record<string, any> };

/** 새 객체의 Fabric 생성자 키 + 초기 props. center=배치 기준점(아트보드 좌표).
 *  도형/선은 center 중심으로, textbox는 center 근처에 배치. DesignEditor가 이 스펙으로
 *  실제 Fabric 인스턴스를 만든다(line은 props.points를 생성자 1번째 인자로 사용). */
export function buildObjectSpec(kind: NewObjectKind, center: { x: number; y: number }): ObjectSpec {
  const { x, y } = center;
  switch (kind) {
    case "rect":
      return { ctor: "rect", props: { left: x - 100, top: y - 60, width: 200, height: 120, fill: "#3b82f6" } };
    case "circle":
      return { ctor: "circle", props: { left: x - 60, top: y - 60, radius: 60, fill: "#10b981" } };
    case "line":
      return { ctor: "line", props: { points: [x - 100, y, x + 100, y], stroke: "#0b1324", strokeWidth: 4 } };
    case "textbox":
    default:
      return { ctor: "textbox", props: { left: x - 150, top: y - 30, width: 300, text: "텍스트를 입력하세요", fontSize: 48, fill: "#0b1324" } };
  }
}
