"use client";

import { useEffect } from "react";
import { initSentry } from "@/lib/sentry";

/** 루트 layout(서버 컴포넌트)에서 클라이언트 1회 init용 빈 컴포넌트. */
export function SentryInit() {
  useEffect(() => {
    initSentry();
  }, []);
  return null;
}
