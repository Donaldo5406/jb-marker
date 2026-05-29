"use client";

import { ImageOff } from "lucide-react";

import { useAuthedBlob } from "@/lib/useAuthedBlob";

export type GalleryMediaProps = {
  runId: string;
  /** /{run}/ 이후 경로 (예: "design/design-system/components/visual/v1.png") */
  rest: string;
  name: string;
};

/** VFS 미디어 썸네일 — useAuthedBlob(JWT)로 blob→objectURL. 실패 시 플레이스홀더. */
export function GalleryMedia({ runId, rest, name }: GalleryMediaProps) {
  const { url, loading, error } = useAuthedBlob(runId, rest);

  if (error) {
    return (
      <div className="flex h-32 w-full flex-col items-center justify-center gap-1 rounded-lg border border-outline-variant bg-surface-container-lowest text-caption text-on-surface-variant">
        <ImageOff className="h-4 w-4" aria-hidden />
        불러오지 못했습니다
      </div>
    );
  }
  if (loading || !url) {
    return (
      <div className="h-32 w-full animate-pulse rounded-lg border border-outline-variant bg-surface-container-high" />
    );
  }
  return (
    <img
      src={url}
      alt={name}
      className="h-32 w-full rounded-lg border border-outline-variant object-cover"
    />
  );
}
