"use client";

import * as React from "react";
import { ImageOff, Loader2 } from "lucide-react";
import { useAuthedBlob } from "@/lib/useAuthedBlob";

export type ImageViewProps = {
  runId: string | null;
  /** openFile.path = `/{runId}/{rest}`. rest는 내부에서 추출. */
  path: string;
};

/** VFS 이미지(PNG 등) 뷰어 — 백엔드가 blob을 raw 바이트로 서빙하므로 텍스트가 아닌
 *  useAuthedBlob(JWT)로 받아 <img>로 표시한다. 에디터 중앙 패널의 이미지 분기 본문. */
export function ImageView({ runId, path }: ImageViewProps) {
  const rest = runId ? path.replace(`/${runId}/`, "") : null;
  const { url, loading, error } = useAuthedBlob(runId, rest);

  if (loading) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-surface px-8 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden />
        <p className="text-body-sm text-on-surface-variant">이미지 불러오는 중…</p>
      </div>
    );
  }
  if (error || !url) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-surface px-8 text-center">
        <ImageOff className="h-6 w-6 text-outline" aria-hidden />
        <p className="text-body-sm text-on-surface-variant">이미지를 불러오지 못했습니다</p>
      </div>
    );
  }
  return (
    <div className="flex flex-1 items-center justify-center overflow-auto bg-surface-container-lowest p-6">
      {/* 원본 비율 유지·중앙 정렬. 체커보드 없이 surface 위에 표시. */}
      <img
        src={url}
        alt={path.split("/").pop() ?? "이미지"}
        className="max-h-full max-w-full rounded-md border border-outline-variant object-contain shadow-sm"
      />
    </div>
  );
}
