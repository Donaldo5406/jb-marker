"use client";

import * as React from "react";
import { useCockpit } from "./CockpitProvider";

/** spec §8.1 — 5-step PipelineRail. 백엔드 review_state.step과 미러. */
const STEPS: Array<{ id: string; label: string }> = [
  { id: "R0", label: "셋업" },
  { id: "R1", label: "법률 검토" },
  { id: "R2", label: "다국어 동등성" },
  { id: "R3", label: "통합 reconciler" },
  { id: "done", label: "완료" },
];

/** spec §8.1 — 3 페르소나 카드 라벨. 백엔드 R1/R2/R3 액터와 1:1. */
const PERSONA_CARDS: Array<{ node: string; title: string; desc: string }> = [
  { node: "legal", title: "A · 법률 검토관", desc: "표시광고법·금융광고규정 동적 서칭" },
  { node: "i18n", title: "B · 동등성 검토관", desc: "다국어 필수고지 보존·과장 감지" },
  { node: "reconciler", title: "C · 통합 reconciler", desc: "경합 조정·우선순위·권장 종합" },
];

/** ReviewStudio — PipelineRail + 페르소나 카드 + 게이트 패널(ack 버튼) + 액션.
 *  reviewStage·reviewGate·manifest.step_status.review를 사용한 시각 분기(spec §8.1).
 *  BLOCKED → 차단 안내·ack 비노출 / WARN → ack 버튼 / PASS → 진입 가능 메시지. */
export function ReviewStudio() {
  const c = useCockpit();
  const stage = c.reviewStage ?? "R0";
  const gate = c.reviewGate;
  const status = c.manifest?.step_status?.review;

  return (
    <div className="col-span-2 min-h-0 overflow-auto p-6 space-y-6 bg-surface">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-on-surface">ReviewStudio</h2>
        <ol className="flex gap-2 text-sm" aria-label="검토 단계">
          {STEPS.map((s) => (
            <li
              key={s.id}
              data-testid={`review-step-${s.id}`}
              data-active={stage === s.id ? "true" : "false"}
              className={
                "px-3 py-1 rounded-full border " +
                (stage === s.id
                  ? "bg-amber-100 border-amber-400 text-amber-900"
                  : "border-outline-variant text-on-surface-variant")
              }
            >
              {s.label}
            </li>
          ))}
        </ol>
      </header>

      <section className="grid grid-cols-3 gap-3" aria-label="검토 페르소나">
        {PERSONA_CARDS.map((p) => (
          <div
            key={p.node}
            data-testid={`persona-${p.node}`}
            className="p-4 border border-outline-variant rounded-md bg-surface-container-lowest"
          >
            <h3 className="font-medium text-on-surface">{p.title}</h3>
            <p className="text-sm text-on-surface-variant mt-1">{p.desc}</p>
          </div>
        ))}
      </section>

      <section
        className="p-4 border border-outline-variant rounded-md bg-surface-container-lowest"
        aria-label="검토 게이트"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm text-on-surface-variant">게이트:</span>
          <span
            data-testid="gate-badge"
            className={
              "px-2 py-0.5 rounded text-xs font-semibold " +
              (status === "BLOCKED"
                ? "bg-red-100 text-red-800"
                : status === "WARN"
                ? "bg-amber-100 text-amber-800"
                : status === "PASS"
                ? "bg-green-100 text-green-800"
                : "bg-neutral-100 text-neutral-600")
            }
          >
            {status ?? "pending"}
          </span>
          {gate && (
            <span className="text-xs text-on-surface-variant">
              critical {gate.critical} / warning {gate.warning}
            </span>
          )}
        </div>
        {status === "BLOCKED" && (
          <p className="mt-2 text-sm text-red-700">
            critical 위반으로 deploy 진입이 차단되었습니다. DesignStudio에서 수정 후 재검토하세요.
          </p>
        )}
        {status === "WARN" && !c.reviewAcknowledged && (
          <button
            type="button"
            data-testid="ack-button"
            className="mt-2 px-3 py-1.5 rounded bg-amber-600 text-white text-sm hover:bg-amber-700"
            onClick={() => void c.ackReview()}
          >
            경고 확인 후 진행
          </button>
        )}
        {status === "WARN" && c.reviewAcknowledged && (
          <p className="mt-2 text-sm text-amber-700">경고를 확인했습니다. 배포 진입 가능.</p>
        )}
        {status === "PASS" && (
          <p className="mt-2 text-sm text-green-700">위반 없음. 배포 진입 가능.</p>
        )}
      </section>

      <section className="flex gap-2" aria-label="검토 액션">
        {stage === "R0" && (
          <button
            type="button"
            data-testid="run-review"
            className="px-4 py-2 rounded bg-on-surface text-surface text-sm hover:opacity-90"
            onClick={() => void c.runReview()}
          >
            검토 시작
          </button>
        )}
        {stage === "done" && (
          <button
            type="button"
            data-testid="restart-review"
            className="px-4 py-2 rounded border border-outline-variant text-sm text-on-surface hover:bg-surface-container"
            onClick={() => void c.restartReview()}
          >
            재검토
          </button>
        )}
      </section>
    </div>
  );
}
