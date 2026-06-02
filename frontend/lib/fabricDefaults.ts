import { FabricObject } from "fabric";

// fabric v7는 객체 기본 origin을 center로 변경했다(v6는 left/top). 본 프로젝트는
// scene을 left/top 좌표로 조립·직렬화(assembleScene·toObject·loadFromJSON)하므로,
// v6 동작을 보존하기 위해 전역 기본 origin을 left/top으로 복원한다.
//   검증(fabric 7.4.0): Rect({left:100,top:50}) boundingRect.left  -0.5(center) → 100(left).
// 가드: 단위 테스트가 fabric을 vi.mock으로 대체하면 FabricObject가 없을 수 있어 방어한다.
if (FabricObject?.ownDefaults) {
  FabricObject.ownDefaults.originX = "left";
  FabricObject.ownDefaults.originY = "top";
}
