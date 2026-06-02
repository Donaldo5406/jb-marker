"use client";

import Link from "next/link";
import { Check, Sparkles, ArrowLeft, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type Tier = {
  name: string;
  price: string;
  cadence?: string;
  tagline: string;
  features: string[];
  featured?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "₩0",
    tagline: "raw 모델로 가볍게 시작하기",
    features: [
      "Claude · GPT · Gemini 직접 호출",
      "콕핏 워크스페이스 IDE 3분할",
      "가상 폴더 산출물 편집·저장",
      "기획(brainstorming) 스튜디오 체험",
    ],
  },
  {
    name: "Pro",
    price: "₩100,000",
    cadence: "/월",
    tagline: "Marker 모델 + DeployStudio Advisor 풀세트",
    featured: true,
    features: [
      "Free의 모든 기능 포함",
      "Marker 전용 마케팅 모델",
      "DeployStudio Advisor (발송 자동 검토)",
      "디자인 · 검토 · 발송 스튜디오 (순차 제공)",
      "우선 지원",
    ],
  },
];

function handleSubscribe() {
  // Pro 구독은 데모 stub — 실 PG 청구 없음(Deferral D4).
  alert("데모: 콕핏 Setting에서 엔타이틀먼트를 토글하세요");
}

export default function Pricing() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-on-surface">
      {/* 분위기 오브 */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[480px] w-[760px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(94,94,94,0.12),transparent)] blur-3xl" />
      </div>

      <div className="mx-auto max-w-container px-margin-x py-10">
        {/* 상단 네비 */}
        <nav className="flex items-center justify-between text-body-sm text-on-surface-variant">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors hover:bg-surface-container hover:text-on-surface"
          >
            <ArrowLeft className="h-4 w-4" />홈
          </Link>
          <Link
            href="/cockpit"
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors hover:bg-surface-container hover:text-on-surface"
          >
            콕핏<ArrowRight className="h-4 w-4" />
          </Link>
        </nav>

        {/* 헤더 */}
        <div className="mx-auto mt-16 max-w-2xl text-center">
          <p className="mb-4 text-caption uppercase tracking-wider text-on-surface-variant">
            요금제
          </p>
          <h1 className="text-h1 leading-[1.05] tracking-[-0.03em] text-on-surface">
            필요한 만큼만
          </h1>
          <p className="mx-auto mt-5 max-w-md text-body-lg text-on-surface-variant">
            raw 모델로 무료로 시작하고, 마케팅에 특화된 Marker가 필요할 때 Pro로 전환하세요.
          </p>
        </div>

        {/* 티어 카드 */}
        <div className="mx-auto mt-14 grid max-w-4xl gap-6 md:grid-cols-2">
          {TIERS.map((tier) => (
            <Card
              key={tier.name}
              className={cn(
                "relative flex h-full flex-col p-8",
                tier.featured &&
                  "border-primary/30 ring-1 ring-primary/20 shadow-[0_0_60px_rgba(0,0,0,0.05)]",
              )}
            >
              {tier.featured && (
                <span className="absolute right-6 top-6 inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-caption font-medium text-on-primary">
                  <Sparkles className="h-3 w-3" />
                  추천
                </span>
              )}

              <div>
                <h2 className="text-h3 text-on-surface">{tier.name}</h2>
                <p className="mt-1 text-body-sm text-on-surface-variant">{tier.tagline}</p>
              </div>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-h1 leading-none tracking-[-0.03em] text-on-surface">
                  {tier.price}
                </span>
                {tier.cadence && (
                  <span className="text-body-sm text-on-surface-variant">{tier.cadence}</span>
                )}
              </div>

              <ul className="mt-8 space-y-3.5">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-3 text-body-sm text-on-surface">
                    <span
                      className={cn(
                        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                        tier.featured ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface",
                      )}
                    >
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    {f}
                  </li>
                ))}
              </ul>

              <div className="mt-auto pt-10">
                {tier.featured ? (
                  <Button size="lg" className="w-full" onClick={handleSubscribe}>
                    Pro 구독하기
                  </Button>
                ) : (
                  <Link href="/cockpit" className="block">
                    <Button variant="secondary" size="lg" className="w-full">
                      무료로 시작
                    </Button>
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </div>

        {/* 보조 안내 */}
        <p className="mx-auto mt-10 max-w-md text-center text-caption text-on-surface-variant/80">
          데모 환경에서는 실제 결제가 발생하지 않습니다. Pro 기능은 콕핏 Setting의
          엔타이틀먼트 토글로 체험할 수 있습니다.
        </p>
      </div>
    </main>
  );
}
