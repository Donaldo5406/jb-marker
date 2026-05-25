"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, ArrowDown } from "lucide-react";
import { TextRotate } from "@/components/TextRotate";

// TODO(copy): 실제 히어로 카피는 추후 확정. 회전 멘트 placeholder.
const HERO_LINES = ["금융 마케팅을, 더 쉽게", "기획부터 발송까지", "규정은 자동으로"];

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.1 + i * 0.1, duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

export function LandingHero() {
  return (
    <section className="relative overflow-hidden">
      {/* 분위기용 그라데이션 오브(Auralis: 은은한 atmospheric depth) */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-32 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(94,94,94,0.14),transparent)] blur-3xl" />
        <div className="absolute -right-40 top-40 h-[420px] w-[420px] rounded-full bg-[radial-gradient(closest-side,rgba(196,199,199,0.5),transparent)] blur-3xl" />
        {/* 격자 텍스처 — 정밀 엔지니어링 톤 */}
        <div className="absolute inset-0 opacity-[0.4] [background-image:linear-gradient(to_right,rgba(28,27,27,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(28,27,27,0.04)_1px,transparent_1px)] [background-size:64px_64px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_72%)]" />
      </div>

      <div className="mx-auto max-w-container px-margin-x pb-24 pt-24 md:pt-32">
        {/* eyebrow */}
        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mb-7 inline-flex items-center gap-2 rounded-full border border-outline-variant/70 bg-surface-container-lowest/70 px-3.5 py-1.5 text-caption uppercase tracking-wider text-on-surface-variant backdrop-blur-glass"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          AI 마케팅 코파일럿 {/* TODO(copy) */}
        </motion.div>

        {/* 히어로 타이틀: 고정 라인 + 회전 라인 */}
        <h1 className="max-w-[14ch] text-h1 leading-[1.04] tracking-[-0.03em] text-on-surface md:text-[88px]">
          <motion.span custom={1} variants={fadeUp} initial="hidden" animate="show" className="block">
            Marker와 함께 {/* TODO(copy) */}
          </motion.span>
          <span className="mt-1 flex">
            <TextRotate
              texts={HERO_LINES}
              rotationInterval={2600}
              staggerDuration={0.012}
              staggerFrom="first"
              splitBy="characters"
              mainClassName="text-on-surface"
              elementLevelClassName="bg-gradient-to-br from-on-surface to-on-surface-variant bg-clip-text text-transparent"
              transition={{ type: "spring", damping: 28, stiffness: 320 }}
            />
          </span>
        </h1>

        {/* 서브헤드라인 */}
        <motion.p
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-7 max-w-xl text-body-lg text-on-surface-variant"
        >
          {/* TODO(copy) */}
          기획·디자인·규정 검토·발송까지, 금융 마케팅의 전 과정을 하나의 콕핏에서.
          반복은 에이전트에게 맡기고, 의사결정에만 집중하세요.
        </motion.p>

        {/* CTA */}
        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-10 flex flex-wrap items-center gap-3"
        >
          <Link
            href="/cockpit"
            className="group inline-flex h-12 items-center justify-center gap-2 rounded-full bg-primary px-7 text-body-sm font-medium text-on-primary transition-colors hover:bg-primary-container"
          >
            체험해보기
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <a
            href="#pipeline"
            className="group inline-flex h-12 items-center justify-center gap-2 rounded-full bg-surface-container px-7 text-body-sm font-medium text-on-surface transition-colors hover:bg-surface-container-high"
          >
            파이프라인 보기
            <ArrowDown className="h-4 w-4 transition-transform group-hover:translate-y-0.5" />
          </a>
        </motion.div>

        {/* 신뢰 보조 라인 */}
        <motion.p
          custom={5}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-8 text-caption uppercase tracking-wider text-on-surface-variant/80"
        >
          {/* TODO(copy) */}
          신용카드 없이 시작 · 데모 환경 즉시 진입
        </motion.p>
      </div>
    </section>
  );
}
