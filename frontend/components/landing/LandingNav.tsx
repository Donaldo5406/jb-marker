"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, FileText, MessageSquareText, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 랜딩 상단 글래스 네비게이션.
 *
 * 설계 메모: 기존 `DropdownNavigation`은 자체적으로 full-screen `<main>` 래퍼를
 * 렌더하고 top-level 항목에 실제 링크를 연결하지 않으므로(서브메뉴 anchor는 href="#"
 * 하드코딩), 헤더 바로 직접 사용할 수 없다. 대신 그 `navItems` 타입 형태(id/label/
 * subMenus/link)를 그대로 따르되, sticky 글래스 헤더 + 실제 next/link 네비게이션으로
 * 재구성한다. 메뉴: 파이프라인 소개(드롭다운) / 작업 내역(History 딥링크) + CTA 체험해보기
 * (결제 메뉴는 2026-07-04 결제 표면 폐기로 제거).
 */

type SubItem = { label: string; description: string; icon: React.ElementType; link?: string };
type NavItem = {
  id: number;
  label: string;
  link?: string;
  subMenus?: { title: string; items: SubItem[] }[];
};

const NAV_ITEMS: NavItem[] = [
  {
    id: 1,
    label: "파이프라인 소개",
    link: "/#pipeline",
    subMenus: [
      {
        title: "워크플로",
        items: [
          { label: "기획", description: "브레인스토밍부터 카피까지", icon: MessageSquareText, link: "/#step-planning" },
          { label: "디자인", description: "소재·포스터 자동 생성", icon: Sparkles, link: "/#step-design" },
          { label: "검토·발송", description: "규정 검토 후 배포", icon: FileText, link: "/#step-review" },
        ],
      },
    ],
  },
  { id: 4, label: "작업 내역", link: "/cockpit?view=history" },
];

export function LandingNav() {
  const [openMenu, setOpenMenu] = React.useState<number | null>(null);

  return (
    <header className="sticky top-0 z-[60] w-full">
      <div className="mx-auto flex h-header max-w-container items-center justify-between gap-6 border-b border-outline-variant/50 bg-surface/70 px-margin-x backdrop-blur-glass">
        {/* 로고 */}
        <Link href="/" className="group flex items-center gap-2.5">
          <img src="/brand/jb-symbol.png" alt="JB 금융그룹 심볼" className="h-8 w-8 rounded-md" />
          <span className="text-body-lg font-semibold tracking-tight text-on-surface">JB Marker</span>
        </Link>

        {/* 중앙 메뉴 */}
        <nav className="relative hidden items-center md:flex" aria-label="주요">
          {NAV_ITEMS.map((item) => (
            <div
              key={item.id}
              className="relative"
              onMouseEnter={() => setOpenMenu(item.id)}
              onMouseLeave={() => setOpenMenu(null)}
            >
              <Link
                href={item.link ?? "#"}
                className="group relative flex items-center gap-1 rounded-full px-4 py-1.5 text-body-sm font-medium text-on-surface/70 transition-colors hover:bg-surface-container-lowest/70 hover:text-on-surface"
              >
                <span>{item.label}</span>
                {item.subMenus && (
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform duration-300",
                      openMenu === item.id && "rotate-180",
                    )}
                  />
                )}
                {openMenu === item.id && (
                  <motion.span
                    layoutId="nav-hover"
                    className="absolute inset-0 -z-10 rounded-full bg-surface-container-high"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
              </Link>

              <AnimatePresence>
                {openMenu === item.id && item.subMenus && (
                  <div className="absolute left-0 top-full pt-3">
                    <motion.div
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.18, ease: "easeOut" }}
                      className="w-max rounded-xl border border-outline-variant/60 bg-surface-container-lowest/90 p-4 shadow-ambient backdrop-blur-glass"
                    >
                      {item.subMenus.map((sub) => (
                        <div key={sub.title}>
                          <p className="mb-3 text-caption uppercase tracking-wider text-on-surface-variant">
                            {sub.title}
                          </p>
                          <ul className="space-y-1">
                            {sub.items.map(({ label, description, icon: Icon, link: subLink }) => (
                              <li key={label}>
                                <Link
                                  href={subLink ?? item.link ?? "#"}
                                  className="group flex items-start gap-3 rounded-lg p-2 transition-colors hover:bg-surface-container"
                                >
                                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-outline-variant/70 text-on-surface-variant transition-colors group-hover:border-primary group-hover:text-on-surface">
                                    <Icon className="h-[18px] w-[18px]" />
                                  </span>
                                  <span className="leading-5">
                                    <span className="block text-body-sm font-medium text-on-surface">
                                      {label}
                                    </span>
                                    <span className="block text-caption font-normal text-on-surface-variant">
                                      {description}
                                    </span>
                                  </span>
                                </Link>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </motion.div>
                  </div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </nav>

        {/* 우측 CTA */}
        <div className="flex items-center gap-2">
          <Link
            href="/cockpit"
            className="inline-flex h-9 items-center justify-center gap-1.5 rounded-full bg-primary px-5 text-caption font-medium text-on-primary transition-colors hover:bg-primary-container"
          >
            체험해보기
            <Sparkles className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </header>
  );
}
