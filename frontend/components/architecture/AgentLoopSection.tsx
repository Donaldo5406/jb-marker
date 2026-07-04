"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * AI 에이전트 섹션 — AI 지휘부(하네스)의 내부 동작을 두 축으로 보여준다.
 * 좌: 공통 에이전트 루프(6단계 순환 점등 + 궤도 파티클), 우: 4종 하네스별 세부 스텝.
 * 평가 기준 "Agent 활용" 대응 — 도구 사용·자기 검증·HITL·영속 기억을 명시한다.
 */

const TICK_MS = 1400;
const INK = "#051d49";
const MUT = "#47536b";
const DIM = "#6b7891";
const LINE = "#c3ccda";
const PRIMARY = "#0054a7"; // globals.css --color-primary

const LOOP_STEPS: { title: string; sub: string; cap: string }[] = [
  { title: "① 상태 읽기", sub: "저장소에서 맥락 불러오기", cap: "지금까지의 기획서·산출물을 저장소에서 불러와 맥락을 잡습니다." },
  { title: "② 계획", sub: "이번 턴 할 일 스스로 결정", cap: "이번 턴에 무엇을 할지 에이전트가 스스로 결정합니다." },
  { title: "③ 도구 호출", sub: "검색 · 생성 · 검수 도구 선택", cap: "웹 검색 · 이미지 생성 · 법령 검색 · 화면 검수 중 필요한 도구를 골라 씁니다." },
  { title: "④ 자체 검증", sub: "미달이면 스스로 한 번 더", cap: "결과물을 스스로 점검하고, 기준에 못 미치면 한 번 더 다듬습니다." },
  { title: "⑤ 사용자 게이트", sub: "승인 · 재생성 · 질문", cap: "사람에게 묻습니다 — 승인 · 재생성 · 질문. 최종 결정권은 항상 사람에게." },
  { title: "⑥ 상태 기록", sub: "다음 턴의 기억으로 저장", cap: "산출물과 진행 상태를 저장소에 남깁니다 — 다음 턴과 다른 하네스의 기억이 됩니다." },
];

// 시계방향 6방위(상단 시작) 노드 중심 좌표 — viewBox 460x445 기준
const LOOP_POS: { cx: number; cy: number }[] = [
  { cx: 230, cy: 70 },
  { cx: 360, cy: 145 },
  { cx: 360, cy: 295 },
  { cx: 230, cy: 370 },
  { cx: 100, cy: 295 },
  { cx: 100, cy: 145 },
];

const HARNESSES: { color: string; name: string; role: string; steps: string; gate: string }[] = [
  {
    color: "#0054a7", // primary
    name: "기획 하네스",
    role: "무엇을 만들지 대화로 확정",
    steps: "멀티턴 대화 → 웹 검색으로 근거 수집 → 기획서 → 실행계획",
    gate: "충분성 게이트 — 필수 항목이 모두 채워져야 제작 단계로 넘어갑니다",
  },
  {
    color: "#9a6212", // severity.warning
    name: "이미지 하네스",
    role: "포스터 제작",
    steps: "준비 → 초안 ◈ → 시각 → 문구 → 브랜드 → 최종 ◈ (◈ = AI 자체 점검)",
    gate: "단계마다 사용자 게이트 — 승인해야 다음 단계로 진행",
  },
  {
    color: "#0098d7", // accent
    name: "영상 하네스",
    role: "영상 제작",
    steps: "준비 → 스토리보드 → 장면 생성 → 문구 → 브랜드 → 최종 렌더",
    gate: "렌더 후 필수 고지 3초 노출을 기계가 재검증 — 미달이면 차단",
  },
  {
    color: "#ba1a1a", // severity.critical
    name: "검토 하네스",
    role: "준법 사전심의",
    steps: "실제 법령 검색 → AI 화면 검수 → 통과 / 주의 / 차단 판정",
    gate: "차단이면 발송 잠금 — 검토를 통과해야만 발송 가능",
  },
];

const FEATURES = ["스스로 도구 선택", "자기 검증 루프", "사람이 최종 결정 (HITL)", "파일로 남는 기억"];

export function AgentLoopSection() {
  const reduced = useReducedMotion();
  const [cur, setCur] = React.useState(0);

  React.useEffect(() => {
    if (reduced) return;
    const id = window.setInterval(() => setCur((c) => (c + 1) % LOOP_STEPS.length), TICK_MS);
    return () => window.clearInterval(id);
  }, [reduced]);

  return (
    <section id="agent" className="relative scroll-mt-header">
      <div className="mx-auto max-w-container px-margin-x py-24">
        <div className="max-w-2xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant"
          >
            AI 에이전트
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="text-h2 tracking-[-0.02em] text-on-surface"
          >
            AI를 한 번 부르고<br />끝내지 않습니다
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-5 text-body-lg text-on-surface-variant"
          >
            도구와 기억을 가진 에이전트가 아래 루프를 돌며 산출물을 완성하고, 중요한
            갈림길마다 사람의 결정을 거칩니다.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-6 flex flex-wrap gap-2"
          >
            {FEATURES.map((f) => (
              <span
                key={f}
                className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-caption font-medium text-primary"
              >
                {f}
              </span>
            ))}
          </motion.div>
        </div>

        <div className="mt-14 grid gap-5 lg:grid-cols-[minmax(330px,460px)_1fr]">
          {/* 에이전트 루프 다이어그램 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col rounded-[24px] border border-outline-variant/70 bg-surface-container-lowest/80 p-4 shadow-elev-1 backdrop-blur-glass"
          >
            <svg
              viewBox="0 0 460 445"
              role="img"
              aria-label="에이전트 루프: 상태 읽기, 계획, 도구 호출, 자체 검증, 사용자 게이트, 상태 기록의 순환"
              className="block h-auto w-full"
            >
              <path
                id="al-orbit"
                fill="none"
                stroke={LINE}
                strokeWidth={1.4}
                strokeDasharray="4 5"
                d="M 230 70 A 150 150 0 1 1 230 370 A 150 150 0 1 1 230 70"
              />
              <text x={230} y={212} textAnchor="middle" fontSize={15} fontWeight={800} fill={INK}>
                에이전트 루프
              </text>
              <text x={230} y={233} textAnchor="middle" fontSize={10.5} fill={MUT}>
                도구 · 기억 · 자기검증 · 사람의 결정
              </text>

              {LOOP_STEPS.map((s, i) => {
                const { cx, cy } = LOOP_POS[i];
                const on = reduced || i === cur;
                return (
                  <g
                    key={s.title}
                    className={cn("transition-opacity duration-500", on ? "opacity-100" : "opacity-60")}
                  >
                    <rect
                      x={cx - 84} y={cy - 27} width={168} height={54} rx={9}
                      fill="#ffffff"
                      stroke={on ? PRIMARY : LINE}
                      strokeWidth={on ? 1.6 : 1}
                      style={{
                        transition: "stroke .4s ease, filter .4s ease",
                        filter: on && !reduced ? "drop-shadow(0 0 8px rgba(0,84,167,0.35))" : undefined,
                      }}
                    />
                    <text x={cx} y={cy - 6} textAnchor="middle" fontSize={12.5} fontWeight={700} fill={INK}>
                      {s.title}
                    </text>
                    <text x={cx} y={cy + 13} textAnchor="middle" fontSize={9.5} fill={MUT}>
                      {s.sub}
                    </text>
                  </g>
                );
              })}

              {/* 궤도 파티클 — repeatCount indefinite라 삽입 시점과 무관하게 항상 순환 */}
              {!reduced && (
                <circle r={5} fill={PRIMARY} style={{ filter: "drop-shadow(0 0 6px rgba(0,84,167,0.6))" }}>
                  <animateMotion dur="8.4s" repeatCount="indefinite">
                    <mpath href="#al-orbit" />
                  </animateMotion>
                </circle>
              )}
            </svg>
            <p className="min-h-[44px] px-2 pt-2 text-center text-caption font-normal text-on-surface-variant">
              {reduced ? (
                "에이전트는 이 여섯 단계를 반복하며 산출물을 완성합니다."
              ) : (
                <>
                  <b className="font-semibold text-primary">
                    {cur + 1}. {LOOP_STEPS[cur].title.slice(2)}
                  </b>{" "}
                  — {LOOP_STEPS[cur].cap}
                </>
              )}
            </p>
          </motion.div>

          {/* 4종 하네스 세부 스텝 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col justify-center rounded-[24px] border border-outline-variant/70 bg-surface-container-lowest/80 px-7 py-2 shadow-elev-1 backdrop-blur-glass"
          >
            {HARNESSES.map((h) => (
              <div key={h.name} className="border-b border-outline-variant/40 py-4 last:border-b-0">
                <p className="flex items-center gap-2 text-body-sm font-semibold text-on-surface">
                  <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: h.color }} />
                  {h.name}
                  <span className="text-caption font-normal text-outline">{h.role}</span>
                </p>
                <p className="mt-1.5 text-body-sm text-on-surface">{h.steps}</p>
                <p className="mt-1 text-caption font-normal text-on-surface-variant">{h.gate}</p>
              </div>
            ))}
          </motion.div>
        </div>

        {/* 게이트 3분기 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-[24px] border border-outline-variant/70 bg-surface-container-lowest/80 px-7 py-4 text-body-sm text-on-surface-variant shadow-elev-1 backdrop-blur-glass"
        >
          <span className="font-semibold text-on-surface">사용자 게이트의 세 갈래</span>
          <span>
            <b className="font-semibold text-severity-ok">승인</b> → 다음 단계로 전진
          </span>
          <span>
            <b className="font-semibold text-severity-warning">다시</b> → AI가 지시문을 스스로 다듬어 재생성
          </span>
          <span>
            <b className="font-semibold text-primary">건너뛰기</b> → AI가 대신 점검하고, 경고를 달아 자동 전진
          </span>
        </motion.div>
      </div>
    </section>
  );
}
