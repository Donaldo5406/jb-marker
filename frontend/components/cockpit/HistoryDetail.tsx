"use client";

import * as React from "react";
import { ArrowLeft, FileText, Play } from "lucide-react";
import { api, type GalleryResponse, type GalleryItem } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { GalleryMedia } from "./GalleryMedia";
import { PreviewFrame } from "./PreviewFrame";

type LoadState = "loading" | "ok" | "error";

/** "/{run}/..." 경로에서 run 세그먼트를 떼어 GalleryMedia용 rest로. */
function toRest(runId: string, path: string): string {
  const prefix = `/${runId}/`;
  return path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\//, "");
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
    <div className="flex-1 overflow-y-auto bg-surface px-6 py-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <header className="flex items-center justify-between gap-4">
          <Button variant="secondary" size="sm" onClick={onBack}>
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            목록
          </Button>
          <h1 className="min-w-0 flex-1 truncate text-h3 text-on-surface">
            {data?.run.title?.trim() || "작업 상세"}
          </h1>
          <Button variant="primary" size="sm" onClick={() => onContinue(runId)}>
            <Play className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            이어서 작업
          </Button>
        </header>

        {state === "loading" && (
          <Card className="p-8 text-center text-body-sm text-on-surface-variant">
            불러오는 중…
          </Card>
        )}
        {state === "error" && (
          <Card className="p-8 text-center text-body-sm text-on-surface-variant">
            작업 상세를 불러오지 못했습니다.
          </Card>
        )}

        {state === "ok" && data && (
          <div className="space-y-8">
            {data.sections.map((sec) => (
              <section key={sec.studio} className="space-y-3">
                <div className="flex items-center gap-2">
                  <h2 className="text-body-lg font-semibold text-on-surface">{sec.label}</h2>
                  <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-caption text-on-surface-variant">
                    {sec.status}
                  </span>
                </div>

                {sec.has_preview && <PreviewFrame runId={runId} />}

                {sec.groups.length === 0 ? (
                  <p className="text-body-sm text-on-surface-variant">
                    아직 산출물이 없습니다.
                  </p>
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
                            className="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2"
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
          </div>
        )}
      </div>
    </div>
  );
}
