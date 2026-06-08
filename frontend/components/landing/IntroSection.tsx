"use client";

import { motion } from "motion/react";
import { PenLine, Wand2, ShieldCheck, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/Card";

const STEPS = [
  {
    step: "01",
    icon: PenLine,
    title: "기획",
    anchor: "step-planning",
    body: "브레인스토밍부터 메시지 카피까지, 캠페인의 뼈대를 함께 잡습니다.",
  },
  {
    step: "02",
    icon: Wand2,
    title: "디자인",
    anchor: "step-design",
    body: "포스터·소재를 자동 생성하고, 에디터에서 손쉽게 다듬습니다.",
  },
  {
    step: "03",
    icon: ShieldCheck,
    title: "검토·발송",
    anchor: "step-review",
    body: "금융 규정을 자동 검토한 뒤, 채널로 안전하게 배포합니다.",
  },
];

export function IntroSection() {
  return (
    <section id="pipeline" className="relative scroll-mt-header">
      <div className="mx-auto max-w-container px-margin-x py-24">
        {/* 섹션 헤더 */}
        <div className="max-w-2xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant"
          >
            이용 방식
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="text-h2 tracking-[-0.02em] text-on-surface"
          >
            하나의 파이프라인,<br />세 번의 흐름.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-5 text-body-lg text-on-surface-variant"
          >
            각 단계는 콕핏에서 이어지는 하나의 작업 흐름입니다. 산출물은 가상 폴더에
            쌓이고, 언제든 되돌아가 편집할 수 있습니다.
          </motion.p>
        </div>

        {/* 3단계 카드 */}
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {STEPS.map(({ step, icon: Icon, title, body, anchor }, i) => (
            <motion.div
              key={step}
              id={anchor}
              className="scroll-mt-header"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
            >
              <Card className="group relative h-full overflow-hidden p-7 transition-colors hover:border-outline-variant">
                {/* 워터마크 단계 번호 */}
                <span
                  aria-hidden
                  className="pointer-events-none absolute -right-2 -top-4 select-none text-[88px] font-semibold leading-none tracking-tighter text-on-surface/[0.04]"
                >
                  {step}
                </span>

                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-container text-on-surface transition-colors group-hover:bg-primary group-hover:text-on-primary">
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </span>

                <h3 className="mt-6 flex items-center gap-2 text-h3 text-on-surface">
                  {title}
                  {i < STEPS.length - 1 && (
                    <ArrowRight className="h-4 w-4 text-outline opacity-0 transition-opacity group-hover:opacity-100" />
                  )}
                </h3>
                <p className="mt-2.5 text-body-sm text-on-surface-variant">{body}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
