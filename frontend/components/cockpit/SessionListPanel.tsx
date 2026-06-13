"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LIFECYCLE_STUDIOS } from "@/lib/cockpit-nav";
import type { SessionListItem, SessionStatus } from "@/lib/api";
import { useCockpit } from "./CockpitProvider";

const STUDIO_LABEL: Record<string, string> = {
  brainstorming: "기획", design: "디자인", review: "검토", video: "영상", deploy: "배포",
};
const STATUS_LABEL: Record<SessionStatus, string> = {
  active: "활성", suspended: "일시중지", archived: "만료",
};
const STATUS_DOT: Record<SessionStatus, string> = {
  active: "bg-primary motion-safe:animate-pulse", suspended: "bg-secondary", archived: "border border-outline-variant",
};

function fmtMs(ms: number | null): string {
  if (ms == null) return "-";
  return new Date(ms).toLocaleString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** 활성 세션 목록 — 순수 프레젠테이션. 5 LIFECYCLE_STUDIOS 기준, 응답에 없는 studio는 '미시작'. */
export function SessionListPanelView({ sessions, onRefresh }: { sessions: SessionListItem[]; onRefresh: () => void }) {
  const byStudio = new Map(sessions.map((s) => [s.studio, s]));
  return (
    <Card className="space-y-4 p-6">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-h3 text-on-surface">세션</h2>
          <p className="text-body-sm text-on-surface-variant">스튜디오별 세션 상태와 만료 시각</p>
        </div>
        <Button variant="secondary" size="sm" onClick={onRefresh}>
          <RefreshCw className="mr-1 h-3.5 w-3.5" aria-hidden /> 새로고침
        </Button>
      </div>
      <ul className="divide-y divide-outline-variant/50 overflow-hidden rounded-[20px] border border-outline-variant bg-surface-container-lowest">
        {LIFECYCLE_STUDIOS.map((studio) => {
          const s = byStudio.get(studio);
          return (
            <li key={studio} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 rounded-full ${s ? STATUS_DOT[s.status] : "border border-outline-variant"}`} aria-hidden />
                <span className="text-body-sm text-on-surface">{STUDIO_LABEL[studio] ?? studio}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-caption text-on-surface-variant">{s ? STATUS_LABEL[s.status] : "미시작"}</span>
                {s?.expires_at != null && (
                  <span className="text-caption text-on-surface-variant">만료 {fmtMs(s.expires_at)}</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** context 구독 컨테이너 — 마운트 시 1회 listSessions. */
export function SessionListPanel() {
  const c = useCockpit();
  React.useEffect(() => { void c.refreshSessions(); }, [c.refreshSessions]);
  return <SessionListPanelView sessions={c.sessionList} onRefresh={() => void c.refreshSessions()} />;
}
