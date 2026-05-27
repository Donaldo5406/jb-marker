"use client";

import * as React from "react";
import { Coins, Image as ImageIcon, MessageSquare } from "lucide-react";
import { api, type UsageSummary } from "@/lib/api";
import { Card } from "@/components/ui/Card";

/** USD를 자릿수에 따라 보기 좋게: 1$ 이상이면 $X.XX, 미만이면 $X.XXXX. */
function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd >= 1) return `$${usd.toFixed(2)}`;
  if (usd >= 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(6)}`;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

const STEP_LABEL: Record<string, string> = {
  brainstorming: "Brainstorming",
  design: "Design",
  review: "Review",
  deploy: "Deploy",
  advisor: "Advisor (D2)",
  gateway: "Gateway",
};

export type UsagePanelProps = {
  runId: string;
};

/** History 행 펼침 시 표시되는 토큰·비용 패널 — runId 변경 시 자동 fetch. */
export function UsagePanel({ runId }: UsagePanelProps) {
  const [data, setData] = React.useState<UsageSummary | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getUsage(runId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError("사용량을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (loading) {
    return (
      <Card className="mt-2 p-4 text-caption text-on-surface-variant" data-testid={`usage-loading-${runId}`}>
        사용량 로딩 중…
      </Card>
    );
  }
  if (error) {
    return (
      <Card className="mt-2 p-4 text-caption text-error" data-testid={`usage-error-${runId}`}>
        {error}
      </Card>
    );
  }
  if (!data || data.total.calls === 0) {
    return (
      <Card className="mt-2 p-4 text-caption text-on-surface-variant" data-testid={`usage-empty-${runId}`}>
        아직 기록된 LLM 호출이 없습니다.
      </Card>
    );
  }

  const stepRows = Object.entries(data.by_step).sort((a, b) => b[1].cost_usd - a[1].cost_usd);

  return (
    <Card className="mt-2 space-y-3 p-4" data-testid={`usage-panel-${runId}`}>
      <div className="flex flex-wrap items-center gap-3 text-body-sm">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-surface-container-high px-2 py-1 font-medium text-on-surface">
          <Coins className="h-3.5 w-3.5" aria-hidden />
          {formatCost(data.total.cost_usd)}
        </span>
        <span className="inline-flex items-center gap-1.5 text-on-surface-variant">
          <MessageSquare className="h-3.5 w-3.5" aria-hidden />
          in {formatTokens(data.total.input_tokens)} · out {formatTokens(data.total.output_tokens)}
        </span>
        {data.total.images > 0 && (
          <span className="inline-flex items-center gap-1.5 text-on-surface-variant">
            <ImageIcon className="h-3.5 w-3.5" aria-hidden />
            {data.total.images}장
          </span>
        )}
        <span className="text-caption text-outline">호출 {data.total.calls}회</span>
      </div>

      <table className="w-full text-left text-caption">
        <thead>
          <tr className="text-on-surface-variant">
            <th className="pb-1 font-medium">단계</th>
            <th className="pb-1 text-right font-medium">호출</th>
            <th className="pb-1 text-right font-medium">in</th>
            <th className="pb-1 text-right font-medium">out</th>
            <th className="pb-1 text-right font-medium">이미지</th>
            <th className="pb-1 text-right font-medium">비용</th>
          </tr>
        </thead>
        <tbody>
          {stepRows.map(([step, s]) => (
            <tr key={step} className="border-t border-outline-variant/40">
              <td className="py-1.5 text-on-surface">{STEP_LABEL[step] ?? step}</td>
              <td className="py-1.5 text-right text-on-surface-variant">{s.calls}</td>
              <td className="py-1.5 text-right text-on-surface-variant">{formatTokens(s.input_tokens)}</td>
              <td className="py-1.5 text-right text-on-surface-variant">{formatTokens(s.output_tokens)}</td>
              <td className="py-1.5 text-right text-on-surface-variant">{s.images || "-"}</td>
              <td className="py-1.5 text-right font-medium text-on-surface">{formatCost(s.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="text-caption text-outline">
        비용 추정치 — 공시 단가 기반(USD). 실제 빌링은 provider 콘솔 확인.
      </p>
    </Card>
  );
}
