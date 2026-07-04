"use client";

import Link from "next/link";
import { LayoutGroup, motion } from "motion/react";
import { ArrowRight, ArrowDown } from "lucide-react";
import { TextRotate } from "@/components/TextRotate";
import Floating, { FloatingElement } from "@/components/ui/parallax-floating";

const HERO_LINES = ["더 빠르게", "더 쉽게", "자동으로", "한 번에"];

// demo.tsx의 exampleImages 배치를 우리 5장 컬러 이미지로 매핑.
// (depth, top/left, size, rotate는 demo.tsx 값 그대로 유지)
const exampleImages = [
  { src: "/landing/corner-ml.jpg", alt: "" }, // 작은 액센트
  { src: "/landing/corner-tl.jpg", alt: "" }, // 좌상 큰
  { src: "/landing/corner-bl.jpg", alt: "" }, // 좌하 큰
  { src: "/landing/corner-tr.jpg", alt: "" }, // 우상 큰
  { src: "/landing/corner-br.jpg", alt: "" }, // 우하 큰
];

export function LandingHero() {
  return (
    <section className="relative flex h-[calc(100vh-72px)] w-full flex-col items-center justify-center overflow-hidden md:overflow-visible">
      {/* demo.tsx의 Floating(시차) + FloatingElement 5장 — 위치/크기/회전 모두 demo 그대로 */}
      <Floating sensitivity={-0.5} className="h-full">
        <FloatingElement
          depth={0.5}
          className="top-[18%] left-[7%] md:top-[27%] md:left-[10%]"
        >
          <motion.img
            src={exampleImages[0].src}
            alt={exampleImages[0].alt}
            className="h-12 w-16 -rotate-[3deg] cursor-pointer rounded-xl object-cover shadow-2xl transition-transform duration-200 hover:scale-105 sm:h-16 sm:w-24 md:h-20 md:w-28 lg:h-24 lg:w-32"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          />
        </FloatingElement>

        <FloatingElement
          depth={1}
          className="top-[3%] left-[13%] md:top-[9%] md:left-[16%]"
        >
          <motion.img
            src={exampleImages[1].src}
            alt={exampleImages[1].alt}
            className="h-28 w-40 -rotate-12 cursor-pointer rounded-xl object-cover shadow-2xl transition-transform duration-200 hover:scale-105 sm:h-36 sm:w-48 md:h-44 md:w-56 lg:h-48 lg:w-60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
          />
        </FloatingElement>

        <FloatingElement
          depth={4}
          className="top-[80%] left-[15%] md:top-[70%] md:left-[17%]"
        >
          <motion.img
            src={exampleImages[2].src}
            alt={exampleImages[2].alt}
            className="h-40 w-40 -rotate-[4deg] cursor-pointer rounded-xl object-cover shadow-2xl transition-transform duration-200 hover:scale-105 sm:h-48 sm:w-48 md:h-60 md:w-60 lg:h-64 lg:w-64"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9 }}
          />
        </FloatingElement>

        <FloatingElement
          depth={2}
          className="top-[3%] left-[80%] md:top-[5%] md:left-[76%]"
        >
          <motion.img
            src={exampleImages[3].src}
            alt={exampleImages[3].alt}
            className="h-36 w-40 rotate-[6deg] cursor-pointer rounded-xl object-cover shadow-2xl transition-transform duration-200 hover:scale-105 sm:h-44 sm:w-48 md:h-52 md:w-60 lg:h-56 lg:w-64"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1 }}
          />
        </FloatingElement>

        <FloatingElement
          depth={1}
          className="top-[73%] left-[76%] md:top-[63%] md:left-[74%]"
        >
          <motion.img
            src={exampleImages[4].src}
            alt={exampleImages[4].alt}
            className="h-44 w-44 rotate-[19deg] cursor-pointer rounded-xl object-cover shadow-2xl transition-transform duration-200 hover:scale-105 sm:h-64 sm:w-64 md:h-72 md:w-72 lg:h-80 lg:w-80"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.3 }}
          />
        </FloatingElement>
      </Floating>

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
          <span className="flex items-center justify-center gap-2">
            {/* 워드마크: PNG를 mask로 쓰고 광택 그라데이션으로 채워 '윤기(글로시)' 표현 */}
            <span
              role="img"
              aria-label="JB Marker"
              className="inline-block h-[2em] aspect-[756/284]"
              style={{
                WebkitMaskImage: "url(/landing/jb-marker-wordmark.png)",
                maskImage: "url(/landing/jb-marker-wordmark.png)",
                WebkitMaskSize: "contain",
                maskSize: "contain",
                WebkitMaskRepeat: "no-repeat",
                maskRepeat: "no-repeat",
                WebkitMaskPosition: "center",
                maskPosition: "center",
                backgroundImage:
                  "linear-gradient(178deg,#0a0a0a 0%,#000 32%,#6e6e6e 50%,#000 68%,#0a0a0a 100%)",
                filter: "drop-shadow(0 2px 5px rgba(0,0,0,0.22))",
              }}
            />
            <span>와 함께</span>
          </span>
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
