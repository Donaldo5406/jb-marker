"use client";
import * as React from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { useAuthedBlob } from "@/lib/useAuthedBlob";
import { useVideoTimeline } from "./useVideoTimeline";
import {
  activeLayers, disclosureExposure, layerText, shotAt,
  CANVAS_W, CANVAS_H, DISCLOSURE_MIN_SEC, type VideoLayer,
} from "@/lib/video/storyboard";
import { cn } from "@/lib/utils";

const LANE_ROLES = ["headline", "body", "cta", "disclosure"] as const;

export type VideoEditorProps = {
  content: string;
  runId: string | null;
  lang: string;
  rendering: boolean;
  onRender: () => void | Promise<void>;
  onSave: (content: string) => void | Promise<void>;
};

/** storyboard.spec.json 편집기 — 9:16 DOM 오버레이 프록시 프리뷰 + 타임라인 + 슬림 인스펙터.
 *  고지 누적 노출 < 3초면 "확정 → 렌더" 차단(서버 재검증). 최종 mp4는 백엔드 ffmpeg가 번인. */
export function VideoEditor({ content, runId, lang, rendering, onRender, onSave }: VideoEditorProps) {
  const t = useVideoTimeline(content);
  const sb = t.sb;

  // footage blob — Hook은 조건부 return 이전에 무조건 호출(Rules of Hooks).
  const curShot = sb ? shotAt(sb, t.time) : null;
  const footageRest = curShot
    ? `video/design-system/components/footage/clip_${curShot.id}.mp4`
    : null;
  const footage = useAuthedBlob(runId, footageRest);
  const [videoBroke, setVideoBroke] = React.useState(false);
  React.useEffect(() => setVideoBroke(false), [footage.url]);

  if (!sb) {
    return (
      <div data-testid="video-editor-empty"
        className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
        <p className="text-body-lg font-medium text-on-surface">영상 콘티 대기</p>
        <p className="max-w-sm text-body-sm text-on-surface-variant">
          유효한 storyboard.spec.json이 없습니다. 콘티(V1)가 생성되면 여기서 편집할 수 있습니다.
        </p>
      </div>
    );
  }

  const duration = t.duration || 1;
  const overlays = activeLayers(sb, t.time);
  const exposure = disclosureExposure(sb);
  const discOk = exposure >= DISCLOSURE_MIN_SEC;

  const selLayer: VideoLayer | null =
    t.sel && sb.shots ? sb.shots.find((s) => s.id === t.sel!.shotId)?.layers?.[t.sel.layerIdx] ?? null : null;

  const rulerRef = React.useRef<HTMLDivElement>(null);
  const seekFromEvent = (clientX: number) => {
    const el = rulerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
    t.seek(ratio * duration);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <Group orientation="horizontal" className="min-h-0 flex-1 overflow-hidden">
        <Panel id="ve-preview" defaultSize={t.sel ? 70 : 100} minSize={48}
          className="min-h-0 overflow-hidden">
          <div className="flex h-full items-center justify-center bg-surface-container-lowest p-4">
            <div data-testid="video-preview"
              className="relative h-full max-h-full overflow-hidden rounded-lg shadow-ambient"
              style={{ aspectRatio: "9 / 16", containerType: "size",
                background: sb.bg_color ?? "#0B2B5B" }}>
              {footage.url && !videoBroke && (
                <video src={footage.url} muted loop playsInline
                  onError={() => setVideoBroke(true)}
                  className="absolute inset-0 h-full w-full object-cover" />
              )}
              {footage.url && videoBroke && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={footage.url} alt="" className="absolute inset-0 h-full w-full object-cover" />
              )}
              {overlays.map((l, i) => {
                const b = l.bbox ?? { x: 80, y: 800, w: 920, h: 200 };
                const text = layerText(sb, l, lang);
                return (
                  <div key={`${l.role}-${i}`}
                    className="absolute flex items-center"
                    style={{
                      left: `${(b.x / CANVAS_W) * 100}%`,
                      top: `${(b.y / CANVAS_H) * 100}%`,
                      width: `${(b.w / CANVAS_W) * 100}%`,
                      color: l.color ?? "#FFFFFF",
                      fontSize: `${((l.font_px ?? 48) / CANVAS_W) * 100}cqw`,
                      lineHeight: 1.1, fontWeight: l.role === "headline" ? 800 : 500,
                      textShadow: "0 1px 4px rgba(0,0,0,0.5)",
                    }}>
                    {text || <span className="opacity-40">[{l.role}]</span>}
                  </div>
                );
              })}
            </div>
          </div>
        </Panel>
        {t.sel && selLayer && (
          <>
            <Separator className="w-px bg-outline-variant" />
            <Panel id="ve-inspector" defaultSize={30} minSize={20}
              className="min-h-0 overflow-y-auto border-l border-outline-variant bg-surface-container-low">
              <div className="flex flex-col gap-3 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-body-sm font-medium text-on-surface">{selLayer.role}</span>
                  <button type="button" onClick={t.clearSelection}
                    className="text-caption text-on-surface-variant hover:text-on-surface">닫기</button>
                </div>
                <label className="flex flex-col gap-1">
                  <span className="text-caption text-on-surface-variant">문구 ({lang})</span>
                  <textarea data-testid="inspector-copy" rows={3}
                    className="rounded-md border border-outline-variant bg-surface px-2 py-1.5 text-body-sm text-on-surface"
                    value={layerText(sb, selLayer, lang)}
                    onChange={(e) => t.editCopy(lang, selLayer.copy_key || selLayer.role, e.target.value)} />
                </label>
                <div className="flex gap-2">
                  <label className="flex flex-1 flex-col gap-1">
                    <span className="text-caption text-on-surface-variant">in (초)</span>
                    <input data-testid="inspector-in" type="number" step="0.1" value={selLayer.in ?? 0}
                      onChange={(e) => t.editLayerTiming(t.sel!.shotId, t.sel!.layerIdx, "in", Number(e.target.value))}
                      className="rounded-md border border-outline-variant bg-surface px-2 py-1.5 text-body-sm" />
                  </label>
                  <label className="flex flex-1 flex-col gap-1">
                    <span className="text-caption text-on-surface-variant">out (초)</span>
                    <input data-testid="inspector-out" type="number" step="0.1" value={selLayer.out ?? 0}
                      onChange={(e) => t.editLayerTiming(t.sel!.shotId, t.sel!.layerIdx, "out", Number(e.target.value))}
                      className="rounded-md border border-outline-variant bg-surface px-2 py-1.5 text-body-sm" />
                  </label>
                </div>
                {curShot?.camera && (
                  <div className="text-caption text-on-surface-variant">카메라(읽기전용): {curShot.camera}</div>
                )}
              </div>
            </Panel>
          </>
        )}
      </Group>

      <div className="border-t border-outline-variant bg-surface-container-low px-3 py-2">
        <div className="mb-1 flex items-center gap-2">
          <button type="button" data-testid="play-toggle" onClick={() => t.setPlaying(!t.playing)}
            className="rounded-md bg-surface-container-high px-2 py-1 text-caption text-on-surface">
            {t.playing ? "❚❚" : "▶"}
          </button>
          <span className="text-caption tabular-nums text-on-surface-variant">
            {t.time.toFixed(1)} / {duration.toFixed(1)}s
          </span>
        </div>
        <div ref={rulerRef} data-testid="timeline-ruler"
          onClick={(e) => seekFromEvent(e.clientX)}
          className="relative mb-1 h-4 cursor-pointer rounded bg-surface-container-high">
          <div className="absolute top-0 h-full w-0.5 bg-primary"
            style={{ left: `${(t.time / duration) * 100}%` }} />
        </div>
        <div className="relative mb-1 flex h-6 w-full gap-px">
          {(sb.shots ?? []).map((s) => (
            <div key={s.id} data-testid={`video-shot-${s.id}`}
              className="flex items-center justify-center overflow-hidden rounded bg-[#3a4a6b] text-caption text-white/80"
              style={{ width: `${((s.end - s.start) / duration) * 100}%` }}>
              {s.id}
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-px">
          {LANE_ROLES.map((role) => (
            <div key={role} className="relative h-5 w-full rounded bg-surface-container">
              {(sb.shots ?? []).flatMap((s) =>
                (s.layers ?? []).map((l, idx) =>
                  l.role === role ? (
                    <button key={`${s.id}-${idx}`} type="button"
                      data-testid={`video-layer-${s.id}-${idx}`}
                      onClick={() => t.selectLayer(s.id, idx)}
                      className={cn("absolute top-0 h-full rounded px-1 text-[10px] text-white",
                        role === "disclosure" ? "bg-[#7a5cff]" : "bg-primary",
                        t.sel?.shotId === s.id && t.sel?.layerIdx === idx && "ring-2 ring-on-surface")}
                      style={{ left: `${((l.in ?? 0) / duration) * 100}%`,
                        width: `${(((l.out ?? 0) - (l.in ?? 0)) / duration) * 100}%` }}>
                      {role}
                    </button>
                  ) : null,
                ),
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-outline-variant bg-surface-container-low px-3 py-2">
        <div data-testid="disclosure-meter"
          className={cn("text-caption", discOk ? "text-on-surface-variant" : "text-error font-medium")}>
          고지 노출 {exposure}s / {DISCLOSURE_MIN_SEC}s {discOk ? "✓" : "⚠ 미달"}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button type="button" data-testid="save-storyboard" disabled={!t.dirty}
            onClick={() => onSave(t.serialized())}
            className="rounded-md border border-outline-variant px-3 py-1.5 text-body-sm text-on-surface disabled:opacity-40">
            저장
          </button>
          <button type="button" data-testid="confirm-render" disabled={!discOk || rendering}
            onClick={() => void onRender()}
            className="rounded-md bg-primary px-3 py-1.5 text-body-sm font-medium text-on-primary disabled:opacity-40">
            {rendering ? "렌더 중…" : "확정 → 렌더"}
          </button>
        </div>
      </div>
    </div>
  );
}
