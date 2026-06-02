"use client";

import * as React from "react";
import { ArrowLeft, FileText, Play } from "lucide-react";
import { api, type GalleryResponse, type GalleryItem } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { GalleryMedia } from "./GalleryMedia";
import { PreviewFrame } from "./PreviewFrame";
import { UsagePanel } from "./UsagePanel";

type LoadState = "loading" | "ok" | "error";

/** "/{run}/..." 경로에서 run 세그먼트를 떼어 GalleryMedia용 rest로. */
function toRest(runId: string, path: string): string {
  const prefix = `/${runId}/`;
  return path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\//, "");
}

/** 섹션 상태 → 점 색. RunList의 상태 어휘와 일치(완료=짙은 점, 진행=펄스, 그외=빈 링). */
function sectionDot(status: string): string {
  if (status === "done") return "bg-primary";
  if (status === "active") return "bg-secondary motion-safe:animate-pulse";
  return "border border-outline-variant";
}

export type HistoryDetailProps = {
  runId: string;
  onBack: () => void;
  onContinue: (runId: string) => void;
};

/** History 상세 갤러리 — 단계별 섹션으로 아티팩트 정렬, design-system iframe 프리뷰. */
export function HistoryDetail({ runId, onBack, onContinue }: HistoryDetailProps) {
  const [data, setData] = React.useState<GalleryResponse | null>(null);
  const [state, setState] = React.useState<LoadState>("loading");

  React.useEffect(() => {
    let cancelled = false;
    setState("loading");
    api
      .getGallery(runId)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setState("ok");
        }
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-surface">
      {/* 글라스 헤더 — 긴 갤러리에서도 목록/이어서-작업을 항상 노출. */}
      <div className="border-b border-outline-variant/50 bg-surface/80 backdrop-blur-glass">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-6 py-4">
          <Button variant="secondary" size="sm" onClick={onBack} className="shrink-0 gap-1.5">
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            목록
          </Button>
          <h1 className="min-w-0 flex-1 truncate text-center text-h3 text-on-surface">
            {data?.run.title?.trim() || "작업 상세"}
          </h1>
          <Button
            variant="primary"
            size="sm"
            onClick={() => onContinue(runId)}
            className="shrink-0 gap-1.5"
          >
            <Play className="h-3.5 w-3.5" aria-hidden />
            이어서 작업
          </Button>
        </div>
      </div>

      {/* 스크롤 영역 */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl space-y-8 px-6 py-8">
          {state === "loading" && (
            <div className="rounded-[20px] border border-outline-variant bg-surface-container-lowest p-8 text-center text-body-sm text-on-surface-variant shadow-ambient">
              불러오는 중…
            </div>
          )}
          {state === "error" && (
            <div className="rounded-[20px] border border-outline-variant bg-surface-container-lowest p-8 text-center text-body-sm text-on-surface-variant shadow-ambient">
              작업 상세를 불러오지 못했습니다.
            </div>
          )}

          {state === "ok" && data && (
            <>
              {/* 사용량·비용을 상세 뷰 상단에 배치 — 탐색기에서 숨긴 usage/log.jsonl의 직관적 대체. */}
              <section className="space-y-3">
                <h2 className="text-body-lg font-semibold text-on-surface">사용량 · 비용</h2>
                <UsagePanel runId={runId} />
              </section>

              {data.sections.map((sec) => (
                <section key={sec.studio} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <h2 className="text-body-lg font-semibold text-on-surface">{sec.label}</h2>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container-high px-2 py-0.5 text-caption text-on-surface-variant">
                      <span className={cn("h-1.5 w-1.5 rounded-full", sectionDot(sec.status))} />
                      {sec.status}
                    </span>
                  </div>

                  {sec.has_preview && <PreviewFrame runId={runId} />}

                  {sec.groups.length === 0 ? (
                    <p className="text-body-sm text-on-surface-variant">아직 산출물이 없습니다.</p>
                  ) : (
                    sec.groups.map((g) => (
                      <div
                        key={g.kind}
                        className={
                          g.items.some((i) => i.is_media)
                            ? "grid grid-cols-2 gap-3 sm:grid-cols-3"
                            : "space-y-2"
                        }
                      >
                        {g.items.map((it: GalleryItem) =>
                          it.is_media ? (
                            <figure key={it.path} className="space-y-1">
                              <GalleryMedia
                                runId={runId}
                                rest={toRest(runId, it.path)}
                                name={it.name}
                              />
                              <figcaption className="truncate text-caption text-on-surface-variant">
                                {it.name}
                              </figcaption>
                            </figure>
                          ) : (
                            <div
                              key={it.path}
                              className="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 transition-colors hover:bg-surface-container-low"
                            >
                              <FileText
                                className="h-4 w-4 shrink-0 text-on-surface-variant"
                                aria-hidden
                              />
                              <span className="truncate text-body-sm text-on-surface">
                                {it.name}
                              </span>
                              <span className="ml-auto shrink-0 text-caption text-outline">
                                {it.source ?? ""}
                              </span>
                            </div>
                          ),
                        )}
                      </div>
                    ))
                  )}
                </section>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
