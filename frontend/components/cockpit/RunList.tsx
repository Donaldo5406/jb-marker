"use client";

import * as React from "react";
import { Clock, FolderOpen, RotateCw } from "lucide-react";
import { api, type Manifest } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";

type LoadState = "loading" | "ok" | "error";

/** created_at(ISO 또는 null)을 사람이 읽기 쉬운 로컬 표기로. 파싱 실패/누락은 "-". */
function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

/** step_status(예: {brainstorming:"done", design:"active"})를 "n/total 완료" 요약으로. */
function summarizeSteps(stepStatus: Record<string, string>): string {
  const entries = Object.entries(stepStatus ?? {});
  if (entries.length === 0) return "단계 기록 없음";
  const done = entries.filter(([, v]) => v === "done").length;
  return `${done}/${entries.length} 단계 완료`;
}

/** History 뷰 — 마운트 시 listRuns()로 run 목록 로딩, 행 클릭 시 openRun. */
export function RunList() {
  const c = useCockpit();
  const [runs, setRuns] = React.useState<Manifest[]>([]);
  const [state, setState] = React.useState<LoadState>("loading");

  const load = React.useCallback(async () => {
    setState("loading");
    try {
      const { runs: rs } = await api.listRuns();
      setRuns(rs);
      setState("ok");
    } catch {
      setState("error");
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="flex-1 overflow-y-auto bg-surface px-6 py-8">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <header className="flex items-end justify-between">
          <div className="space-y-1">
            <h1 className="text-h3 text-on-surface">작업 내역</h1>
            <p className="text-body-sm text-on-surface-variant">
              지난 run을 선택하면 해당 작업 공간으로 이동합니다.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void load()}
            disabled={state === "loading"}
          >
            <RotateCw
              className={cn("mr-1.5 h-3.5 w-3.5", state === "loading" && "animate-spin")}
              aria-hidden
            />
            새로고침
          </Button>
        </header>

        {state === "loading" && (
          <Card className="p-8 text-center text-body-sm text-on-surface-variant">
            불러오는 중…
          </Card>
        )}

        {state === "error" && (
          <Card className="space-y-4 p-8 text-center">
            <p className="text-body-sm text-on-surface-variant">
              작업 내역을 불러오지 못했습니다. 백엔드 연결을 확인하세요.
            </p>
            <Button variant="secondary" size="sm" onClick={() => void load()}>
              다시 시도
            </Button>
          </Card>
        )}

        {state === "ok" && runs.length === 0 && (
          <Card className="flex flex-col items-center gap-3 p-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
              <FolderOpen className="h-5 w-5 text-outline" aria-hidden />
            </div>
            <p className="text-body-lg font-medium text-on-surface">아직 작업이 없습니다</p>
            <p className="max-w-xs text-body-sm text-on-surface-variant">
              Workspace에서 Use Marker로 첫 작업을 시작해 보세요.
            </p>
          </Card>
        )}

        {state === "ok" && runs.length > 0 && (
          <ul className="space-y-3">
            {runs.map((r) => (
              <li key={r.run_id}>
                <button
                  type="button"
                  data-testid={`run-row-${r.run_id}`}
                  onClick={() => void c.openRun(r.run_id)}
                  className="block w-full text-left"
                >
                  <Card className="flex items-center gap-4 p-5 transition-colors hover:bg-surface-container-low">
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className="truncate text-body-lg font-medium text-on-surface">
                        {r.title?.trim() || "제목 없는 작업"}
                      </p>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-on-surface-variant">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" aria-hidden />
                          {formatDate(r.created_at)}
                        </span>
                        <span>{summarizeSteps(r.step_status)}</span>
                      </div>
                    </div>
                    <span className="shrink-0 font-mono text-caption text-outline">
                      {r.run_id.slice(0, 8)}
                    </span>
                  </Card>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
