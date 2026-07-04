"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowDownUp, ChevronDown, Clock, FolderOpen, Play, RotateCw, Search } from "lucide-react";
import { api, type Manifest } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";
import { UsagePanel } from "./UsagePanel";
import { HistoryDetail } from "./HistoryDetail";

type LoadState = "loading" | "ok" | "error";
type StatusFilter = "all" | "in_progress" | "done";
type SortDir = "desc" | "asc";

/** 파이프라인 표준 순서 — step_status 키를 이 순서로 정렬해 일관된 진행 레일을 만든다. */
const STEP_ORDER = ["brainstorming", "design", "review", "deploy"];
const STEP_LABEL: Record<string, string> = {
  brainstorming: "기획",
  design: "디자인",
  review: "검토",
  deploy: "배포",
};
const stepLabel = (key: string) => STEP_LABEL[key] ?? key;

/** 시연(Mock) 모드 작업 내역 — 백엔드 run이 없어도 History를 그럴듯하게 채운다.
 *  created_at은 고정 ISO(결정적). 실제 run과 함께 목록 상단에 표시(표시 전용 샘플). */
const MOCK_RUNS: Manifest[] = [
  { run_id: "demo-jb-youth", title: "JB 주거래 플러스 적금 캠페인", created_at: "2026-06-12T09:00:00Z",
    step_status: { brainstorming: "done", design: "done", review: "done", deploy: "done" } },
  { run_id: "demo-jb-fx-card", title: "BRAVO KOREA 외화 송금 다국어 안내 (ko·en·vi·zh)", created_at: "2026-06-10T14:30:00Z",
    step_status: { brainstorming: "done", design: "done", review: "done" } },
  { run_id: "demo-jb-loan", title: "씨드모아 파킹통장 프로모션", created_at: "2026-06-07T11:15:00Z",
    step_status: { brainstorming: "done", design: "active" } },
];

/** created_at(ISO 또는 null)을 간결한 로컬 표기로. 파싱 실패는 원문, 누락은 "-". */
function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** 정렬 비교용 epoch(ms). 누락/파싱불가는 -Infinity로 밀어 항상 끝으로 보낸다. */
function toEpoch(iso: string | null): number {
  if (!iso) return Number.NEGATIVE_INFINITY;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? Number.NEGATIVE_INFINITY : t;
}

type RunState = {
  total: number;
  done: number;
  kind: "done" | "active" | "idle";
  label: "완료" | "진행 중" | "대기";
  isDone: boolean;
};

/** step_status를 run 단위 상태로 환원 — 필터(완료/진행)와 상태 pill의 단일 출처. */
function runState(stepStatus: Record<string, string>): RunState {
  const entries = Object.entries(stepStatus ?? {});
  const total = entries.length;
  const done = entries.filter(([, v]) => v === "done").length;
  const active = entries.some(([, v]) => v === "active");

  if (total > 0 && done === total) {
    return { total, done, kind: "done", label: "완료", isDone: true };
  }
  if (active || done > 0) {
    return { total, done, kind: "active", label: "진행 중", isDone: false };
  }
  return { total, done, kind: "idle", label: "대기", isDone: false };
}

/** step_status를 파이프라인 순서의 (key,status) 배열로. 진행 레일·단계 칩 공용. */
function orderedSteps(stepStatus: Record<string, string>): { key: string; status: string }[] {
  return Object.keys(stepStatus ?? {})
    .sort((a, b) => {
      const ia = STEP_ORDER.indexOf(a);
      const ib = STEP_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    })
    .map((key) => ({ key, status: stepStatus[key] }));
}

const stepDotClass = (status: string) =>
  status === "done"
    ? "bg-primary"
    : status === "active"
      ? "bg-secondary motion-safe:animate-pulse"
      : "border border-outline-variant";

/** run 단위 상태를 점+라벨 pill로. 완료=짙은 점, 진행=펄스, 대기=빈 링. */
function StatusPill({ state }: { state: RunState }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full bg-surface-container-high px-2 py-0.5 text-caption",
        state.kind === "idle" ? "text-outline" : "text-on-surface-variant",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", stepDotClass(state.kind))} />
      {state.label}
    </span>
  );
}

/** 행 우측의 컴팩트 진행 레일 — 단계별 점으로 한눈에 보이는 파이프라인. */
function StepRail({ steps }: { steps: { key: string; status: string }[] }) {
  if (steps.length === 0) return null;
  return (
    <div className="hidden items-center gap-1.5 sm:flex" aria-hidden>
      {steps.map((s) => (
        <span
          key={s.key}
          title={`${stepLabel(s.key)} · ${s.status}`}
          className={cn("h-1.5 w-1.5 rounded-full", stepDotClass(s.status))}
        />
      ))}
    </div>
  );
}

/** 펼침 영역의 단계 칩 — 레일보다 풍부하게 라벨까지 노출. */
function StepChips({ steps }: { steps: { key: string; status: string }[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {steps.map((s) => (
        <span
          key={s.key}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption",
            s.status === "none"
              ? "bg-surface-container-low text-outline"
              : "bg-surface-container-high text-on-surface",
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", stepDotClass(s.status))} />
          {stepLabel(s.key)}
        </span>
      ))}
    </div>
  );
}

/** 한 run 행 — 좌측 펼침 토글(사용량), 본문 클릭(상세 진입), 우측 이어서-작업. */
function RunRow({
  run,
  expanded,
  onToggle,
  onOpenDetail,
  onContinue,
  reduce,
}: {
  run: Manifest;
  expanded: boolean;
  onToggle: () => void;
  onOpenDetail: () => void;
  onContinue: () => void;
  reduce: boolean;
}) {
  const state = runState(run.step_status);
  const steps = orderedSteps(run.step_status);

  return (
    <li>
      <div className="group flex items-center gap-2 px-4 py-3 transition-colors hover:bg-surface-container-low/70">
        <button
          type="button"
          aria-label={expanded ? "사용량 닫기" : "사용량 보기"}
          aria-expanded={expanded}
          data-testid={`run-toggle-usage-${run.run_id}`}
          onClick={onToggle}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
        >
          <motion.span
            className="flex"
            animate={{ rotate: expanded ? 0 : -90 }}
            transition={{ duration: reduce ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <ChevronDown className="h-4 w-4" aria-hidden />
          </motion.span>
        </button>

        <button
          type="button"
          data-testid={`run-row-${run.run_id}`}
          onClick={onOpenDetail}
          className="flex min-w-0 flex-1 items-center gap-4 rounded-md text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        >
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <StatusPill state={state} />
              <p className="truncate text-body-lg font-medium text-on-surface">
                {run.title?.trim() || "제목 없는 작업"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-on-surface-variant">
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" aria-hidden />
                {formatDate(run.created_at)}
              </span>
              <span aria-hidden className="text-outline-variant">·</span>
              <span className="font-mono text-outline">{run.run_id.slice(0, 8)}</span>
            </div>
          </div>

          {state.total > 0 && (
            <div className="hidden shrink-0 items-center gap-2 sm:flex">
              <StepRail steps={steps} />
              <span className="font-mono text-caption text-on-surface-variant">
                {state.done}/{state.total}
              </span>
            </div>
          )}
        </button>

        <Button
          variant="secondary"
          size="sm"
          aria-label="이어서 작업"
          data-testid={`run-continue-${run.run_id}`}
          onClick={onContinue}
          className="shrink-0 gap-1.5"
        >
          <Play className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline">이어서 작업</span>
        </Button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="expand"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: reduce ? 0 : 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-outline-variant/50 bg-surface-container-low/40"
          >
            <div className="space-y-4 px-4 py-4">
              {steps.length > 0 && (
                <div className="space-y-2">
                  <p className="text-caption uppercase tracking-wide text-on-surface-variant">진행 단계</p>
                  <StepChips steps={steps} />
                </div>
              )}
              <div className="space-y-2">
                <p className="text-caption uppercase tracking-wide text-on-surface-variant">사용량 · 비용</p>
                <UsagePanel runId={run.run_id} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
}

/** 로딩 스켈레톤 행 — 스피너 대신 콘텐츠 형태를 미리 보여 깜빡임을 줄인다. */
function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <ul className="divide-y divide-outline-variant/50">
      {Array.from({ length: count }).map((_, i) => (
        <li key={i} className="flex items-center gap-3 px-4 py-3.5">
          <div className="h-8 w-8 shrink-0 rounded-md bg-surface-container-high motion-safe:animate-pulse" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-4 w-1/2 rounded bg-surface-container-high motion-safe:animate-pulse" />
            <div className="h-3 w-2/5 rounded bg-surface-container-high/70 motion-safe:animate-pulse" />
          </div>
          <div className="hidden h-3 w-10 rounded bg-surface-container-high motion-safe:animate-pulse sm:block" />
        </li>
      ))}
    </ul>
  );
}

const SEGMENTS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "in_progress", label: "진행 중" },
  { value: "done", label: "완료" },
];

/** 진행 상태 세그먼트 컨트롤 — 풀-필 컨테이너에 활성 알약이 떠오르는 형태. */
function StatusSegments({
  value,
  onChange,
}: {
  value: StatusFilter;
  onChange: (v: StatusFilter) => void;
}) {
  return (
    <div className="inline-flex shrink-0 items-center rounded-full bg-surface-container p-1" role="tablist" aria-label="진행 상태 필터">
      {SEGMENTS.map((seg) => {
        const active = value === seg.value;
        return (
          <button
            key={seg.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(seg.value)}
            className={cn(
              "rounded-full px-3 py-1 text-caption transition-colors",
              active
                ? "bg-surface-container-lowest text-on-surface shadow-ambient"
                : "text-on-surface-variant hover:text-on-surface",
            )}
          >
            {seg.label}
          </button>
        );
      })}
    </div>
  );
}

/** History 뷰 — 검색·상태 필터·정렬·펼침 행을 갖춘 인터랙티브 작업 내역. */
export function RunList() {
  const c = useCockpit();
  const reduce = useReducedMotion() ?? false;
  const [runs, setRuns] = React.useState<Manifest[]>([]);
  const [state, setState] = React.useState<LoadState>("loading");
  const [expandedId, setExpandedId] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("all");
  const [sortDir, setSortDir] = React.useState<SortDir>("desc");

  const load = React.useCallback(async () => {
    setState("loading");
    try {
      const { runs: rs } = await api.listRuns();
      // Mock 시연: 실제 run 앞에 시연용 캠페인 내역을 얹어 History를 채운다.
      setRuns(c.mockMode ? [...MOCK_RUNS, ...rs] : rs);
      setState("ok");
    } catch {
      // mock 모드면 백엔드 실패해도 시연용 목록은 보여준다.
      if (c.mockMode) { setRuns(MOCK_RUNS); setState("ok"); }
      else setState("error");
    }
  }, [c.mockMode]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const visible = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = runs.filter((r) => {
      const matchQuery =
        q.length === 0 ||
        (r.title ?? "").toLowerCase().includes(q) ||
        r.run_id.toLowerCase().includes(q);
      if (!matchQuery) return false;
      if (statusFilter === "all") return true;
      const { isDone } = runState(r.step_status);
      return statusFilter === "done" ? isDone : !isDone;
    });
    return filtered.sort((a, b) => {
      const diff = toEpoch(a.created_at) - toEpoch(b.created_at);
      return sortDir === "desc" ? -diff : diff;
    });
  }, [runs, query, statusFilter, sortDir]);

  const resetFilters = () => {
    setQuery("");
    setStatusFilter("all");
  };
  const filtersActive = query.trim().length > 0 || statusFilter !== "all";

  // selectedHistoryRun이 설정되면 목록 대신 상세 갤러리로 토글.
  // (모든 hook 호출 이후에 위치 — rules of hooks 준수.)
  if (c.selectedHistoryRun) {
    return (
      <HistoryDetail
        runId={c.selectedHistoryRun}
        onBack={c.closeHistoryDetail}
        onContinue={(id) => void c.openRun(id)}
      />
    );
  }

  const countLabel =
    visible.length === runs.length
      ? `${runs.length}건`
      : `${visible.length} / ${runs.length}건`;

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-surface">
      {/* 글라스 헤더 — 스크롤과 무관하게 검색·필터를 항상 노출. */}
      <div className="border-b border-outline-variant/50 bg-surface/80 backdrop-blur-glass">
        <div className="mx-auto w-full max-w-3xl space-y-4 px-6 pb-4 pt-8">
          <header className="flex items-end justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h1 className="text-h3 text-on-surface">작업 내역</h1>
                {state === "ok" && runs.length > 0 && (
                  <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-caption text-on-surface-variant">
                    {countLabel}
                  </span>
                )}
              </div>
              <p className="text-body-sm text-on-surface-variant">
                지난 run을 선택하면 해당 작업 공간으로 이동합니다.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void load()}
              disabled={state === "loading"}
              className="gap-1.5"
            >
              <RotateCw
                className={cn("h-3.5 w-3.5", state === "loading" && "motion-safe:animate-spin")}
                aria-hidden
              />
              새로고침
            </Button>
          </header>

          {state === "ok" && runs.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-[12rem] flex-1">
                <Search
                  className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant"
                  aria-hidden
                />
                <Input
                  placeholder="제목 또는 run ID로 검색"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="pl-10"
                  aria-label="작업 검색"
                />
              </div>
              <StatusSegments value={statusFilter} onChange={setStatusFilter} />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
                className="shrink-0 gap-1.5"
                title="정렬 순서 전환"
              >
                <ArrowDownUp className="h-3.5 w-3.5" aria-hidden />
                {sortDir === "desc" ? "최신순" : "오래된순"}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* 스크롤 영역 */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-6 py-6">
          {state === "loading" && (
            <div className="overflow-hidden rounded-[20px] border border-outline-variant bg-surface-container-lowest shadow-ambient">
              <SkeletonRows />
            </div>
          )}

          {state === "error" && (
            <div className="space-y-4 rounded-[20px] border border-outline-variant bg-surface-container-lowest p-8 text-center shadow-ambient">
              <p className="text-body-sm text-on-surface-variant">
                작업 내역을 불러오지 못했습니다. 백엔드 연결을 확인하세요.
              </p>
              <Button variant="secondary" size="sm" onClick={() => void load()}>
                다시 시도
              </Button>
            </div>
          )}

          {state === "ok" && runs.length === 0 && (
            <div className="flex flex-col items-center gap-3 rounded-[20px] border border-outline-variant bg-surface-container-lowest p-12 text-center shadow-ambient">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
                <FolderOpen className="h-5 w-5 text-outline" aria-hidden />
              </div>
              <p className="text-body-lg font-medium text-on-surface">아직 작업이 없습니다</p>
              <p className="max-w-xs text-body-sm text-on-surface-variant">
                Workspace에서 Use Marker로 첫 작업을 시작해 보세요.
              </p>
            </div>
          )}

          {state === "ok" && runs.length > 0 && visible.length === 0 && (
            <div className="flex flex-col items-center gap-3 rounded-[20px] border border-outline-variant bg-surface-container-lowest p-12 text-center shadow-ambient">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-outline-variant bg-surface-container-lowest">
                <Search className="h-5 w-5 text-outline" aria-hidden />
              </div>
              <p className="text-body-lg font-medium text-on-surface">조건에 맞는 작업이 없습니다</p>
              <p className="max-w-xs text-body-sm text-on-surface-variant">
                검색어나 필터를 바꿔 다시 찾아보세요.
              </p>
              {filtersActive && (
                <Button variant="secondary" size="sm" onClick={resetFilters}>
                  필터 초기화
                </Button>
              )}
            </div>
          )}

          {state === "ok" && visible.length > 0 && (
            <ul className="divide-y divide-outline-variant/50 overflow-hidden rounded-[20px] border border-outline-variant bg-surface-container-lowest shadow-ambient">
              {visible.map((r) => (
                <RunRow
                  key={r.run_id}
                  run={r}
                  expanded={expandedId === r.run_id}
                  reduce={reduce}
                  onToggle={() =>
                    setExpandedId((cur) => (cur === r.run_id ? null : r.run_id))
                  }
                  onOpenDetail={() => c.viewHistoryDetail(r.run_id)}
                  onContinue={() => void c.openRun(r.run_id)}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
