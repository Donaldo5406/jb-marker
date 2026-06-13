/** 게이트 액션 식별자→한국어 라벨의 단일 출처.
 *  서버가 GateEnvelope.actions로 선언하는 어휘는 5종(answer/confirm/regenerate/ack/restart);
 *  advance는 요청측 동사(클라이언트가 승인 시 보내는 값, 백엔드 CONFIRM_ACTIONS)로
 *  비-gated 진행 버튼 라벨에 쓰여 여기 포함한다.
 *  핸들러는 각 스튜디오가 컨텍스트에 맞게 바인딩한다
 *  (design의 regenerate=재생성, review의 regenerate=디자인으로 복귀해 재생성). */
export type GateActionId = "confirm" | "advance" | "regenerate" | "restart" | "ack" | "answer";

export const GATE_ACTION_LABELS: Record<GateActionId, string> = {
  confirm: "확정 & 다음 →",
  advance: "다음 단계 →",
  regenerate: "재생성",
  restart: "재검토",
  ack: "경고 확인 후 진행",
  answer: "답변",
};

/** 알 수 없는 식별자는 식별자 자체를 라벨로 반환(백엔드가 새 액션을 추가해도 무해하게 노출). */
export function gateActionLabel(id: string): string {
  return (GATE_ACTION_LABELS as Record<string, string>)[id] ?? id;
}
