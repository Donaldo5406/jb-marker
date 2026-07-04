import type { Metadata } from "next";
import { LandingNav } from "@/components/landing/LandingNav";
import { ArchFlowDiagram } from "@/components/architecture/ArchFlowDiagram";
import { AgentLoopSection } from "@/components/architecture/AgentLoopSection";
import { StackSection } from "@/components/architecture/StackSection";

export const metadata: Metadata = {
  title: "동작 원리 — JB Marker",
  description:
    "JB Marker의 풀스택 구조 — 시스템 흐름, AI 에이전트의 일하는 방식, 기술 스택을 한 페이지로 보여드립니다.",
};

/**
 * 동작 원리 페이지 — 랜딩과 같은 마케팅 표면(bg-background로 body 그라데이션 투과).
 * 섹션 앵커: #flow(시스템 흐름) / #agent(AI 에이전트) / #stack(기술 스택).
 */
export default function ArchitecturePage() {
  return (
    <main className="min-h-screen bg-background text-on-surface">
      <LandingNav />

      {/* 페이지 헤더 */}
      <section className="mx-auto max-w-container px-margin-x pb-0 pt-16">
        <div className="max-w-2xl animate-fade-in-up">
          <p className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant">동작 원리</p>
          <h1 className="text-h2 tracking-[-0.02em] text-on-surface">
            실행 버튼 한 번이
            <br />
            완성물로 돌아오기까지
          </h1>
          <p className="mt-5 text-body-lg text-on-surface-variant">
            JB Marker의 풀스택 구조를 세 장면으로 보여드립니다 — 시스템 흐름, AI
            에이전트의 일하는 방식, 그리고 기술 스택.
          </p>
        </div>
      </section>

      <ArchFlowDiagram />
      <AgentLoopSection />
      <StackSection />

      <footer className="mx-auto max-w-container px-margin-x pb-16">
        <p className="text-caption font-normal text-outline">
          실제 코드를 근거로 그린 다이어그램입니다 — 모든 구성 요소와 흐름은 배포 중인
          시스템과 1:1로 대응합니다.
        </p>
      </footer>
    </main>
  );
}
