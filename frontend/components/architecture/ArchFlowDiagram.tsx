"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 시스템 흐름 다이어그램 — 실행 1턴이 4개 영역(화면·서버·AI·데이터)을 지나는
 * 8단계를 자동 루프로 재생한다. arch-viz 라이트 시각화를 JB Blue 토큰으로 포팅.
 *
 * SVG 내부 색은 클래스 대신 값을 직접 쓴다(토큰 출처: globals.css :root RGB,
 * tailwind.config severity hex). 파티클은 SMIL animateMotion을 명령형으로 붙인다
 * — React 선언 렌더로는 문서 타임라인 기준 begin 제어가 안 되기 때문(beginElement 필요).
 */

const STEP_MS = 3600;

// 토큰과 1:1 대응 — primary/accent(globals.css), warning/ok(severity, tailwind.config)
const ZONE = {
  client: { stroke: "#0098d7", glow: "rgba(0,152,215,0.35)" }, // accent 시안
  server: { stroke: "#0054a7", glow: "rgba(0,84,167,0.35)" }, // primary JB 블루
  ai: { stroke: "#9a6212", glow: "rgba(154,98,18,0.30)" }, // severity.warning
  data: { stroke: "#1f7a4d", glow: "rgba(31,122,77,0.30)" }, // severity.ok
} as const;
const INK = "#051d49";
const MUT = "#47536b";
const DIM = "#6b7891";
const LINE = "#c3ccda";

type ZoneKey = keyof typeof ZONE;
type ParticleSpec = { p: string; dur: number; delay: number; color: string };
type Step = {
  title: string;
  desc: string;
  chips: string[];
  nodes: string[];
  lines: string[];
  particles: ParticleSpec[];
};

const STEPS: Step[] = [
  {
    title: "작업 시작",
    desc: "사용자가 화면에서 실행을 누르면, 로그인 정보와 함께 요청이 서버의 접수 창구(API)로 전달됩니다.",
    chips: ["API 호출", "로그인 토큰 동봉"],
    nodes: ["C1", "C2", "C4", "B1"],
    lines: ["af-l1"],
    particles: [
      { p: "af-l1", dur: 1400, delay: 150, color: ZONE.client.stroke },
      { p: "af-l1", dur: 1400, delay: 600, color: ZONE.client.stroke },
    ],
  },
  {
    title: "권한 확인",
    desc: "서버가 먼저 확인합니다 — 본인의 작업이 맞는지, 유료 기능을 쓸 수 있는 계정인지. 모든 AI 호출이 반드시 이 관문을 지납니다.",
    chips: ["본인 확인", "요금제 확인"],
    nodes: ["B1", "B2"],
    lines: [],
    particles: [],
  },
  {
    title: "담당 AI 배정",
    desc: "작업 종류(기획·이미지·영상·준법검토)에 맞는 전문 AI 진행자가 배정됩니다. 내부 동작은 아래 AI 에이전트 섹션에서 자세히 펼쳐집니다.",
    chips: ["기획", "이미지", "영상", "준법검토"],
    nodes: ["B2", "B3"],
    lines: [],
    particles: [],
  },
  {
    title: "AI 작업 수행",
    desc: "Claude가 기획과 준법 판단을, Google Gemini가 포스터 이미지를, Veo가 영상 장면을 만듭니다. 사용한 AI 비용은 자동으로 기록됩니다.",
    chips: ["Claude 기획·판단", "Gemini 이미지", "Veo 영상", "비용 자동 기록"],
    nodes: ["B3", "B4", "A1", "A2", "A3", "A4"],
    lines: ["af-la1", "af-la2", "af-la3", "af-la4"],
    particles: [
      { p: "af-la1", dur: 1500, delay: 100, color: ZONE.ai.stroke },
      { p: "af-la2", dur: 1500, delay: 420, color: ZONE.ai.stroke },
      { p: "af-la3", dur: 1500, delay: 740, color: ZONE.ai.stroke },
      { p: "af-la4", dur: 1500, delay: 1060, color: ZONE.ai.stroke },
    ],
  },
  {
    title: "자동 검증",
    desc: "결과물이 정해진 단계 순서대로 다듬어지고, 영상은 서버가 직접 최종 렌더링합니다. 필수 고지가 3초 이상 노출되지 않으면 시스템이 자동으로 차단합니다.",
    chips: ["단계별 품질 점검", "고지 3초 규칙 자동 차단"],
    nodes: ["B4", "B5"],
    lines: [],
    particles: [],
  },
  {
    title: "저장",
    desc: "산출물은 종류에 따라 나뉘어 보관됩니다 — 글·기획서·진행 상태는 데이터베이스에, 완성된 이미지·영상 파일은 파일 저장소에.",
    chips: ["데이터베이스", "파일 저장소"],
    nodes: ["B6", "S1", "S2", "S3"],
    lines: ["af-l6a", "af-l6b"],
    particles: [
      { p: "af-l6a", dur: 1400, delay: 150, color: ZONE.data.stroke },
      { p: "af-l6b", dur: 1400, delay: 550, color: ZONE.data.stroke },
    ],
  },
  {
    title: "실시간 알림",
    desc: "작업이 진행되는 동안 서버가 웹소켓으로 화면에 실시간 소식을 보냅니다. 진행 표시줄과 파일 목록이 새로고침 없이 즉시 갱신됩니다.",
    chips: ["웹소켓", "실시간 진행 표시"],
    nodes: ["B1", "C4", "C2"],
    lines: ["af-l7"],
    particles: [
      { p: "af-l7", dur: 1500, delay: 150, color: ZONE.client.stroke },
      { p: "af-l7", dur: 1500, delay: 650, color: ZONE.client.stroke },
    ],
  },
  {
    title: "결과 확인",
    desc: "완성물이 화면에 도착합니다. 에디터에서 글자·이미지를 직접 고칠 수 있고, 히스토리에서 언제든 다시 열 수 있습니다. 흐름은 처음부터 다시 반복됩니다.",
    chips: ["에디터에서 직접 수정", "히스토리 재열람"],
    nodes: ["C1", "C2", "C3"],
    lines: [],
    particles: [],
  },
];

/** 노드 박스 + 텍스트 줄. lines: [폰트크기, dy, 내용, 색] 순서로 그린다. */
type NodeDef = {
  id: string;
  zone: ZoneKey;
  x: number;
  y: number;
  w: number;
  h: number;
  rows: { dy: number; text: string; size: number; weight?: number; color?: string }[];
};

const NODES: NodeDef[] = [
  // ---- 사용자 화면 (client) ----
  { id: "C1", zone: "client", x: 32, y: 92, w: 260, h: 64, rows: [
    { dy: 26, text: "웹 앱", size: 14, weight: 700 },
    { dy: 46, text: "브라우저에서 쓰는 작업 화면 (Next.js)", size: 11 },
  ] },
  { id: "C2", zone: "client", x: 32, y: 170, w: 260, h: 104, rows: [
    { dy: 26, text: "4단계 작업 공간", size: 14, weight: 700 },
    { dy: 47, text: "기획 → 제작(이미지·영상 택일)", size: 11 },
    { dy: 64, text: "→ 준법검토 → 발송", size: 11 },
    { dy: 86, text: "진행 표시줄 · 사용량(비용) 패널", size: 11, color: DIM },
  ] },
  { id: "C3", zone: "client", x: 32, y: 288, w: 260, h: 64, rows: [
    { dy: 26, text: "디자인 에디터", size: 14, weight: 700 },
    { dy: 46, text: "글자·이미지를 레이어로 수정 (Fabric.js)", size: 11 },
  ] },
  { id: "C4", zone: "client", x: 32, y: 366, w: 260, h: 64, rows: [
    { dy: 26, text: "서버 연결 통로", size: 14, weight: 700 },
    { dy: 46, text: "API 요청 · 웹소켓 실시간 수신", size: 11 },
  ] },
  // ---- 중앙 서버 (server) ----
  { id: "B1", zone: "server", x: 388, y: 76, w: 368, h: 58, rows: [
    { dy: 24, text: "요청 접수 창구 (API)", size: 14, weight: 700 },
    { dy: 44, text: "모든 작업 요청이 이 한 곳으로 들어옵니다", size: 11 },
  ] },
  { id: "B2", zone: "server", x: 388, y: 148, w: 368, h: 46, rows: [
    { dy: 18, text: "권한 확인", size: 13, weight: 700 },
    { dy: 36, text: "본인의 작업이 맞는지 · 유료 기능 사용 가능한지 검사", size: 11 },
  ] },
  { id: "B3", zone: "server", x: 388, y: 208, w: 368, h: 92, rows: [
    { dy: 24, text: "AI 지휘부", size: 14, weight: 700 },
    { dy: 44, text: "작업 종류에 맞는 전문 AI 진행자를 배정", size: 11 },
    { dy: 61, text: "기획 · 이미지 · 영상 · 준법검토 4종", size: 11 },
    { dy: 80, text: "AI에게 직접 가지 않고 항상 여기를 거칩니다", size: 11, color: DIM },
  ] },
  { id: "B4", zone: "server", x: 388, y: 314, w: 368, h: 78, rows: [
    { dy: 24, text: "제작 파이프라인 엔진", size: 14, weight: 700 },
    { dy: 44, text: "정해진 단계 순서대로 진행 · 단계마다 품질 점검", size: 11 },
    { dy: 63, text: "중간중간 사용자 확인(승인/재생성)을 받습니다", size: 11, color: DIM },
  ] },
  { id: "B5", zone: "server", x: 388, y: 406, w: 368, h: 64, rows: [
    { dy: 24, text: "안전장치 — 자동 규칙 검사", size: 14, weight: 700 },
    { dy: 44, text: "영상 렌더링 · 필수 고지 3초 자동 검증 · 법규 기반 발송 판정", size: 11 },
  ] },
  { id: "B6", zone: "server", x: 388, y: 484, w: 368, h: 58, rows: [
    { dy: 24, text: "파일 저장 관리자", size: 14, weight: 700 },
    { dy: 44, text: "모든 산출물을 한 체계로 정리해 보관소로 전달", size: 11 },
  ] },
  // ---- 외부 AI (ai) ----
  { id: "A1", zone: "ai", x: 852, y: 76, w: 356, h: 56, rows: [
    { dy: 23, text: "Claude (Anthropic)", size: 14, weight: 700 },
    { dy: 42, text: "기획 대화 · 준법 판단 담당", size: 11 },
  ] },
  { id: "A2", zone: "ai", x: 852, y: 142, w: 356, h: 56, rows: [
    { dy: 23, text: "Gemini 이미지 (Google)", size: 14, weight: 700 },
    { dy: 42, text: "포스터 이미지 생성", size: 11 },
  ] },
  { id: "A3", zone: "ai", x: 852, y: 208, w: 356, h: 56, rows: [
    { dy: 23, text: "Veo (Google)", size: 14, weight: 700 },
    { dy: 42, text: "영상 장면 생성", size: 11 },
  ] },
  { id: "A4", zone: "ai", x: 852, y: 274, w: 356, h: 52, rows: [
    { dy: 22, text: "보조 AI", size: 14, weight: 700 },
    { dy: 40, text: "결과물 화면 검수(Gemini 비전) · 대체 모델(GPT-4o)", size: 11 },
  ] },
  // ---- 데이터 보관소 (data) ----
  { id: "S1", zone: "data", x: 852, y: 392, w: 356, h: 54, rows: [
    { dy: 22, text: "데이터베이스", size: 14, weight: 700 },
    { dy: 41, text: "작업 목록 · 기획서 · 진행 상태", size: 11 },
  ] },
  { id: "S2", zone: "data", x: 852, y: 458, w: 356, h: 54, rows: [
    { dy: 22, text: "파일 저장소", size: 14, weight: 700 },
    { dy: 41, text: "완성된 포스터(PNG) · 영상(MP4)", size: 11 },
  ] },
  { id: "S3", zone: "data", x: 852, y: 524, w: 356, h: 54, rows: [
    { dy: 22, text: "로그인 · 보안", size: 14, weight: 700 },
    { dy: 41, text: "사용자 인증 · 내 작업만 보이게 보호", size: 11 },
  ] },
];

const LINKS: { id: string; d: string; zone: ZoneKey; dashed?: boolean }[] = [
  { id: "af-l1", d: "M 308 124 C 346 124 344 105 386 105", zone: "client" },
  { id: "af-la1", d: "M 758 240 C 806 240 802 104 850 104", zone: "ai" },
  { id: "af-la2", d: "M 758 340 C 806 340 802 170 850 170", zone: "ai" },
  { id: "af-la3", d: "M 758 353 C 810 353 806 236 850 236", zone: "ai" },
  { id: "af-la4", d: "M 758 262 C 814 262 808 300 850 300", zone: "ai" },
  { id: "af-l6a", d: "M 758 513 C 804 513 802 419 850 419", zone: "data" },
  { id: "af-l6b", d: "M 758 513 C 810 513 806 485 850 485", zone: "data" },
  { id: "af-l7", d: "M 386 135 C 340 135 342 404 310 404", zone: "client", dashed: true },
];

const ZONES: { zone: ZoneKey; x: number; y: number; w: number; h: number; label: string }[] = [
  { zone: "client", x: 16, y: 56, w: 292, h: 420, label: "사용자 화면 · Vercel" },
  { zone: "server", x: 372, y: 40, w: 400, h: 524, label: "중앙 서버 · Hugging Face" },
  { zone: "ai", x: 836, y: 40, w: 388, h: 300, label: "외부 AI 모델" },
  { zone: "data", x: 836, y: 364, w: 388, h: 232, label: "데이터 보관소 · Supabase" },
];

export function ArchFlowDiagram() {
  const reduced = useReducedMotion();
  const [cur, setCur] = React.useState(0);
  const [playing, setPlaying] = React.useState(true);
  const layerRef = React.useRef<SVGGElement>(null);
  const timersRef = React.useRef<number[]>([]);

  React.useEffect(() => {
    if (reduced) setPlaying(false);
  }, [reduced]);

  React.useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setCur((c) => (c + 1) % STEPS.length), STEP_MS);
    return () => window.clearInterval(id);
  }, [playing]);

  // SMIL 파티클 — 동적 삽입 요소는 문서 타임라인 기준이라 begin="0s"가 과거가 되어
  // 즉시 종료됨. begin="indefinite" + beginElement()가 유일한 정시 발화 경로.
  React.useEffect(() => {
    if (reduced) return;
    const layer = layerRef.current;
    if (!layer) return;
    const NS = "http://www.w3.org/2000/svg";
    STEPS[cur].particles.forEach((spec) => {
      const t = window.setTimeout(() => {
        const c = document.createElementNS(NS, "circle");
        c.setAttribute("r", "5");
        c.setAttribute("fill", spec.color);
        c.style.filter = `drop-shadow(0 0 6px ${spec.color})`;
        const m = document.createElementNS(NS, "animateMotion");
        m.setAttribute("dur", `${spec.dur}ms`);
        m.setAttribute("begin", "indefinite");
        m.setAttribute("fill", "freeze");
        m.setAttribute("calcMode", "spline");
        m.setAttribute("keyTimes", "0;1");
        m.setAttribute("keySplines", "0.4 0 0.2 1");
        const mp = document.createElementNS(NS, "mpath");
        mp.setAttribute("href", `#${spec.p}`);
        mp.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", `#${spec.p}`);
        m.appendChild(mp);
        c.appendChild(m);
        layer.appendChild(c);
        (m as unknown as { beginElement?: () => void }).beginElement?.(); // jsdom 미지원 가드
        const rm = window.setTimeout(() => c.remove(), spec.dur + 300);
        timersRef.current.push(rm);
      }, spec.delay);
      timersRef.current.push(t);
    });
    return () => {
      timersRef.current.forEach(window.clearTimeout);
      timersRef.current = [];
      while (layer.firstChild) layer.removeChild(layer.firstChild);
    };
  }, [cur, reduced]);

  const step = STEPS[cur];
  const isOn = (id: string) => step.nodes.includes(id);
  const go = (i: number) => setCur((i + STEPS.length) % STEPS.length);

  return (
    <section id="flow" className="relative scroll-mt-header">
      <style>{`@keyframes jbarch-march { to { stroke-dashoffset: -13; } }
@keyframes jbarch-fill { from { width: 0; } to { width: 100%; } }`}</style>
      <div className="mx-auto max-w-container px-margin-x py-24">
        <div className="max-w-2xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant"
          >
            시스템 흐름
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="text-h2 tracking-[-0.02em] text-on-surface"
          >
            작업 한 번이 지나가는 길
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-5 text-body-lg text-on-surface-variant"
          >
            실행 버튼 한 번이 네 개의 영역을 지나 완성물로 돌아옵니다. 여덟 단계가
            자동으로 반복 재생되며, 원하는 단계로 건너뛸 수 있습니다.
          </motion.p>
        </div>

        {/* 다이어그램 스테이지 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="mt-14 overflow-x-auto rounded-[24px] border border-outline-variant/70 bg-surface-container-lowest/80 shadow-elev-2 backdrop-blur-glass"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, #dce6f2 1px, transparent 1.5px)",
            backgroundSize: "26px 26px",
          }}
        >
          <svg
            viewBox="0 0 1240 640"
            role="img"
            aria-label="JB Marker 시스템 흐름: 사용자 화면, 중앙 서버, 외부 AI, 데이터 보관소와 그 사이 데이터 흐름"
            className="block h-auto w-full min-w-[1100px]"
          >
            {ZONES.map((z) => (
              <g key={z.zone}>
                <rect
                  x={z.x} y={z.y} width={z.w} height={z.h} rx={12}
                  fill="rgba(255,255,255,0.5)"
                  stroke={ZONE[z.zone].stroke} strokeOpacity={0.4}
                />
                <text
                  x={z.x + 16} y={z.y + 24}
                  fontSize={11} fontWeight={600} letterSpacing="0.14em" fill={DIM}
                >
                  {z.label.toUpperCase()}
                </text>
              </g>
            ))}

            {LINKS.map((l) => {
              const on = step.lines.includes(l.id);
              return (
                <path
                  key={l.id} id={l.id} d={l.d} fill="none"
                  stroke={on ? ZONE[l.zone].stroke : LINE}
                  strokeWidth={on ? 2.2 : 1.6}
                  opacity={on ? 1 : 0.55}
                  strokeDasharray={on ? "7 6" : l.dashed ? "5 5" : undefined}
                  style={{
                    transition: "stroke .45s ease, opacity .45s ease",
                    animation: on && !reduced ? "jbarch-march 1.1s linear infinite" : undefined,
                  }}
                />
              );
            })}

            {NODES.map((n) => {
              const on = isOn(n.id);
              return (
                <g
                  key={n.id}
                  className={cn("transition-opacity duration-500", on ? "opacity-100" : "opacity-60")}
                >
                  <rect
                    x={n.x} y={n.y} width={n.w} height={n.h} rx={9}
                    fill="#ffffff"
                    stroke={on ? ZONE[n.zone].stroke : LINE}
                    strokeWidth={on ? 1.6 : 1}
                    style={{
                      transition: "stroke .45s ease, filter .45s ease",
                      filter: on ? `drop-shadow(0 0 8px ${ZONE[n.zone].glow})` : undefined,
                    }}
                  />
                  {n.rows.map((r, i) => (
                    <text
                      key={i}
                      x={n.x + 16} y={n.y + r.dy}
                      fontSize={r.size} fontWeight={r.weight ?? 400}
                      fill={r.color ?? (r.weight ? INK : MUT)}
                    >
                      {r.text}
                    </text>
                  ))}
                </g>
              );
            })}

            <g ref={layerRef} aria-hidden />
          </svg>
        </motion.div>

        {/* 재생 콘솔 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          role="group"
          aria-label="시스템 흐름 재생 콘솔"
          className="mt-4 grid grid-cols-1 items-center gap-5 rounded-[24px] border border-outline-variant/70 bg-surface-container-lowest/80 p-6 shadow-elev-1 backdrop-blur-glass md:grid-cols-[auto_1fr_auto]"
        >
          <div className="text-left md:min-w-[76px] md:text-center">
            <span className="text-[30px] font-bold leading-none tabular-nums text-primary">
              {String(cur + 1).padStart(2, "0")}
            </span>
            <span className="mt-1 block text-caption uppercase tracking-widest text-outline">
              / {String(STEPS.length).padStart(2, "0")}
            </span>
          </div>
          <div className="md:min-h-[88px]">
            <h3 className="text-body-lg font-semibold text-on-surface">{step.title}</h3>
            <p className="mt-1 max-w-[78ch] text-body-sm text-on-surface-variant">{step.desc}</p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {step.chips.map((chip) => (
                <span
                  key={chip}
                  className="rounded-md border border-primary/25 bg-primary/5 px-2 py-0.5 text-caption font-medium text-primary"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between gap-4 md:flex-col md:items-end">
            <div className="flex gap-1.5">
              <button
                type="button"
                aria-label="이전 단계"
                onClick={() => go(cur - 1)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-outline-variant bg-surface-container-lowest text-on-surface transition-colors hover:border-primary hover:text-primary"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                aria-label={playing ? "일시정지" : "재생"}
                onClick={() => setPlaying((p) => !p)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-outline-variant bg-surface-container-lowest text-on-surface transition-colors hover:border-primary hover:text-primary"
              >
                {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              </button>
              <button
                type="button"
                aria-label="다음 단계"
                onClick={() => go(cur + 1)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-outline-variant bg-surface-container-lowest text-on-surface transition-colors hover:border-primary hover:text-primary"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <div className="flex gap-1.5">
              {STEPS.map((s, i) => (
                <button
                  key={s.title}
                  type="button"
                  aria-label={`단계 ${i + 1}: ${s.title}`}
                  onClick={() => go(i)}
                  className={cn(
                    "h-2 w-2 rounded-full transition-all duration-300",
                    i === cur ? "scale-125 bg-primary shadow-[0_0_6px_rgba(0,84,167,0.5)]" : "bg-outline-variant",
                  )}
                />
              ))}
            </div>
          </div>
          <div className="h-0.5 overflow-hidden rounded-full bg-surface-container-high md:col-span-3">
            <div
              key={cur}
              className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
              style={
                playing && !reduced
                  ? { animation: `jbarch-fill ${STEP_MS}ms linear forwards` }
                  : { width: "100%" }
              }
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
