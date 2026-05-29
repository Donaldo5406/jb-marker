"use client";

import { useEffect, useState } from "react";
import { api, authedFetch } from "./api";

export type AuthedBlobState = { url: string | null; loading: boolean; error: boolean };

/** authedFetch(JWT)로 VFS 블롭을 받아 objectURL 생성. 언마운트/인자 변경 시 revoke.
 *  iframe이 아닌 <img src>용 — img는 JWT 헤더를 못 실어 직접 fetch가 필요하다. */
export function useAuthedBlob(
  runId: string | null,
  rest: string | null,
): AuthedBlobState {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!runId || !rest) {
      setUrl(null);
      setLoading(false);
      setError(false);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(false);
    authedFetch(api.assetUrl(runId, rest))
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [runId, rest]);

  return { url, loading, error };
}
