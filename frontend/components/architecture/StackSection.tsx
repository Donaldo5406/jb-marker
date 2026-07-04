"use client";

import { motion } from "motion/react";
import { Layers, ShieldCheck, Workflow } from "lucide-react";
import { Card } from "@/components/ui/Card";

/**
 * 기술 스택 섹션 — 제작 파이프라인·준법 게이트·운영 체계 카드 3장과
 * 구성 요소별 기술 표. 내용은 배포 중인 시스템과 1:1 대응(과장 배제).
 */

const CARDS: { icon: typeof Workflow; title: string; lead: string; items: string[] }[] = [
  {
    icon: Workflow,
    title: "제작 파이프라인",
    lead: "이미지: 초안 → 시각 → 문구 → 브랜드 → 최종 · 영상: 스토리보드 → 장면 → 최종 렌더",
    items: [
      "글자는 이미지에 굽지 않습니다 — 별도 레이어로 두어 금리 숫자 오류(AI 환각)를 원천 차단",
      "필수 고지·로고는 기계가 자동 부착 — AI가 아니라 정해진 규칙이 정확한 위치에 배치",
      "각 단계마다 사용자가 확인하고 승인 또는 재생성을 선택",
    ],
  },
  {
    icon: ShieldCheck,
    title: "준법·발송 — 사전심의 내장",
    lead: "준법검토 = 실제 법령 검색 + AI 화면 검수 → 통과 / 주의 / 차단",
    items: [
      "차단이면 다음 단계 잠금 — 검토를 통과해야만 발송으로 넘어갑니다",
      "영상의 필수 고지 3초 노출은 기계가 자동 측정 — 미달이면 시스템이 스스로 차단",
      "발송 가능 여부는 AI 판단이 아니라 법규 기반 규칙(정보통신망법 · 개인정보보호법)이 판정",
    ],
  },
  {
    icon: Layers,
    title: "운영 — 자동 배포·자동 점검",
    lead: "코드 수정 → 자동 배포: 화면은 Vercel · 서버는 Hugging Face",
    items: [
      "30분마다 자동 상태 점검 — 서버가 잠들지 않게 스스로 깨어 있음",
      "데모 모드 — AI 비용 없이 전체 흐름을 그대로 시연 가능",
      "AI 사용 비용을 작업 단위로 자동 집계 — 화면의 사용량 패널에 표시",
    ],
  },
];

const STACK_ROWS: { area: string; tech: string[]; role: string }[] = [
  { area: "사용자 화면", tech: ["Next.js", "React"], role: "브라우저에서 쓰는 작업 화면 — 4단계 작업 공간과 히스토리" },
  { area: "에디터", tech: ["Fabric.js"], role: "글자·이미지를 레이어 단위로 수정 — 글자를 이미지에 굽지 않음" },
  { area: "중앙 서버", tech: ["FastAPI", "Python", "ffmpeg"], role: "전체 흐름 지휘 · 권한 확인 · 영상 최종 렌더링" },
  { area: "AI 모델", tech: ["Claude", "Gemini", "Veo", "GPT-4o"], role: "기획·준법 판단 / 포스터 이미지 / 영상 장면 / 화면 검수" },
  { area: "데이터 보관", tech: ["Supabase"], role: "데이터베이스 · 파일 저장소 · 로그인과 보안" },
  { area: "배포·운영", tech: ["Vercel", "Hugging Face", "GitHub Actions"], role: "코드 수정 시 자동 배포 · 30분마다 자동 상태 점검" },
];

export function StackSection() {
  return (
    <section id="stack" className="relative scroll-mt-header">
      <div className="mx-auto max-w-container px-margin-x py-24">
        <div className="max-w-2xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant"
          >
            기술 스택
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="text-h2 tracking-[-0.02em] text-on-surface"
          >
            구성 요소별 기술
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-5 text-body-lg text-on-surface-variant"
          >
            모든 구성 요소와 흐름은 배포 중인 시스템과 1:1로 대응합니다.
          </motion.p>
        </div>

        {/* 특성 카드 3장 */}
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {CARDS.map(({ icon: Icon, title, lead, items }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
            >
              <Card className="group h-full p-7 transition-colors hover:border-outline-variant">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-container text-on-surface transition-colors group-hover:bg-primary group-hover:text-on-primary">
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </span>
                <h3 className="mt-6 text-h3 text-on-surface">{title}</h3>
                <p className="mt-2.5 rounded-lg border border-outline-variant/60 bg-surface-container-low px-3 py-2 text-caption font-medium text-on-surface">
                  {lead}
                </p>
                <ul className="mt-3 space-y-2 text-body-sm text-on-surface-variant">
                  {items.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span aria-hidden className="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-outline" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* 스택 표 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="mt-5 overflow-hidden rounded-[24px] border border-outline-variant bg-surface-container-lowest shadow-elev-1"
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-body-sm">
              <thead>
                <tr className="border-b border-outline-variant/60 text-left">
                  <th className="px-6 py-3.5 text-caption uppercase tracking-wider text-on-surface-variant">구성 요소</th>
                  <th className="px-6 py-3.5 text-caption uppercase tracking-wider text-on-surface-variant">기술</th>
                  <th className="px-6 py-3.5 text-caption uppercase tracking-wider text-on-surface-variant">하는 일</th>
                </tr>
              </thead>
              <tbody>
                {STACK_ROWS.map((row) => (
                  <tr key={row.area} className="border-b border-outline-variant/40 last:border-b-0">
                    <td className="whitespace-nowrap px-6 py-3.5 font-medium text-on-surface">{row.area}</td>
                    <td className="px-6 py-3.5">
                      <span className="flex flex-wrap gap-1.5">
                        {row.tech.map((t) => (
                          <code
                            key={t}
                            className="rounded bg-surface-container px-1.5 py-0.5 font-mono text-[12px] text-primary"
                          >
                            {t}
                          </code>
                        ))}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-on-surface-variant">{row.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
