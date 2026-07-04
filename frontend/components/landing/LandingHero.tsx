"use client";

import Link from "next/link";
import { LayoutGroup, motion } from "motion/react";
import { ArrowRight, ArrowDown } from "lucide-react";
import { TextRotate } from "@/components/TextRotate";
import { FacetField } from "@/components/landing/FacetField";

const HERO_LINES = ["더 빠르게", "더 쉽게", "자동으로", "한 번에"];

export function LandingHero() {
  return (
    <section className="relative flex h-[calc(100vh-72px)] w-full flex-col items-center justify-center overflow-hidden md:overflow-visible">
      {/* JB 심볼 패싯 그래픽 — 사진 대신 브랜드 모티브를 시차 배치 */}
      <FacetField />

      {/* 콘텐츠: demo.tsx의 중앙 좁은 컬럼 + z-50 */}
      <div className="pointer-events-auto z-50 flex w-[250px] flex-col items-center justify-center sm:w-[300px] md:w-[500px] lg:w-[700px]">
        {/* eyebrow */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="mb-7 inline-flex items-center gap-2 rounded-full border border-outline-variant/70 bg-surface-container-lowest/70 px-3.5 py-1.5 text-caption uppercase tracking-wider text-on-surface-variant backdrop-blur-glass"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          AI 마케팅 코파일럿
        </motion.div>

        {/* h1: demo.tsx의 LayoutGroup + motion.span inline 회전 패턴 그대로 */}
        <motion.h1
          className="flex w-full flex-col items-center justify-center whitespace-pre text-center text-3xl font-semibold leading-tight tracking-tight text-on-surface sm:text-5xl md:space-y-2 md:text-7xl lg:text-8xl"
          animate={{ opacity: 1, y: 0 }}
          initial={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3, ease: "easeOut", delay: 0.3 }}
        >
          <span>Marker와 함께</span>
          <LayoutGroup>
            <motion.span layout className="flex whitespace-pre">
              <TextRotate
                texts={HERO_LINES}
                rotationInterval={5000}
                staggerDuration={0.025}
                staggerFrom="first"
                splitBy="characters"
                mainClassName="overflow-hidden px-2 py-0 pb-2 text-on-surface md:pb-4"
                elementLevelClassName="bg-gradient-to-br from-on-surface to-on-surface-variant bg-clip-text text-transparent"
                transition={{ type: "spring", damping: 34, stiffness: 280 }}
              />
            </motion.span>
          </LayoutGroup>
        </motion.h1>

        {/* 서브헤드라인 */}
        <motion.p
          className="pt-6 text-center text-sm text-on-surface-variant sm:pt-8 sm:text-base md:pt-10 md:text-lg lg:pt-12 lg:text-xl"
          animate={{ opacity: 1, y: 0 }}
          initial={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3, ease: "easeOut", delay: 0.5 }}
        >
          기획·디자인·규정 검토·발송까지, 금융 마케팅의 전 과정을 하나의 콕핏에서.
        </motion.p>

        {/* CTA */}
        <motion.div
          className="mt-10 flex flex-row items-center justify-center gap-3 sm:mt-12 md:mt-14"
          animate={{ opacity: 1, y: 0 }}
          initial={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3, ease: "easeOut", delay: 0.7 }}
        >
          <Link
            href="/cockpit"
            className="group inline-flex h-12 items-center justify-center gap-2 rounded-full bg-primary px-7 text-body-sm font-medium text-white transition-colors hover:bg-primary-container"
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
      </div>
    </section>
  );
}
