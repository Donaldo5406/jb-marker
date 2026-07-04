"use client";

import { motion } from "motion/react";
import Floating, { FloatingElement } from "@/components/ui/parallax-floating";

// JB 심볼마크 패싯 램프(밝음→어두움) — 디자인 스펙 §3 실측값.
const RAMP = ["#0098D7", "#008CCF", "#007AC6", "#0067B6", "#0054A7", "#004898", "#004294", "#092C86"] as const;

type Quad = readonly [string, string, string, string];

function FacetPiece({ colors, className }: { colors: Quad; className?: string }) {
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className={className} aria-hidden focusable="false">
      <polygon points="0,0 100,0 50,50" fill={colors[0]} />
      <polygon points="0,0 50,50 0,100" fill={colors[1]} />
      <polygon points="100,0 100,100 50,50" fill={colors[2]} />
      <polygon points="0,100 50,50 100,100" fill={colors[3]} />
    </svg>
  );
}

// 배치·깊이·회전·등장 딜레이는 기존 corner-*.jpg 5장의 값을 그대로 승계.
const PIECES: {
  depth: number; pos: string; size: string; rotate: string; delay: number; op: number; colors: Quad;
}[] = [
  { depth: 0.5, pos: "top-[18%] left-[7%] md:top-[27%] md:left-[10%]",
    size: "h-12 w-16 sm:h-16 sm:w-24 md:h-20 md:w-28 lg:h-24 lg:w-32",
    rotate: "-rotate-[3deg]", delay: 0.5, op: 0.6, colors: [RAMP[0], RAMP[1], RAMP[2], RAMP[3]] },
  { depth: 1, pos: "top-[3%] left-[13%] md:top-[9%] md:left-[16%]",
    size: "h-28 w-40 sm:h-36 sm:w-48 md:h-44 md:w-56 lg:h-48 lg:w-60",
    rotate: "-rotate-12", delay: 0.7, op: 0.7, colors: [RAMP[1], RAMP[3], RAMP[2], RAMP[5]] },
  { depth: 4, pos: "top-[80%] left-[15%] md:top-[70%] md:left-[17%]",
    size: "h-40 w-40 sm:h-48 sm:w-48 md:h-60 md:w-60 lg:h-64 lg:w-64",
    rotate: "-rotate-[4deg]", delay: 0.9, op: 0.5, colors: [RAMP[2], RAMP[4], RAMP[5], RAMP[7]] },
  { depth: 2, pos: "top-[3%] left-[80%] md:top-[5%] md:left-[76%]",
    size: "h-36 w-40 sm:h-44 sm:w-48 md:h-52 md:w-60 lg:h-56 lg:w-64",
    rotate: "rotate-[6deg]", delay: 1.1, op: 0.6, colors: [RAMP[0], RAMP[2], RAMP[3], RAMP[6]] },
  { depth: 1, pos: "top-[73%] left-[76%] md:top-[63%] md:left-[74%]",
    size: "h-44 w-44 sm:h-64 sm:w-64 md:h-72 md:w-72 lg:h-80 lg:w-80",
    rotate: "rotate-[19deg]", delay: 1.3, op: 0.4, colors: [RAMP[3], RAMP[5], RAMP[6], RAMP[7]] },
];

export function FacetField() {
  return (
    <Floating sensitivity={-0.5} className="h-full">
      {PIECES.map((p, i) => (
        <FloatingElement key={i} depth={p.depth} className={p.pos}>
          <motion.div
            className={`${p.size} ${p.rotate} overflow-hidden rounded-xl shadow-elev-3 transition-transform duration-200 hover:scale-105`}
            initial={{ opacity: 0 }}
            animate={{ opacity: p.op }}
            transition={{ delay: p.delay }}
          >
            <FacetPiece colors={p.colors} className="h-full w-full" />
          </motion.div>
        </FloatingElement>
      ))}
    </Floating>
  );
}
