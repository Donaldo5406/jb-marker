"use client";

import * as React from "react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type Manifest, type Provider, type VfsNode } from "@/lib/api";
import { useRunSocket } from "@/lib/useRunSocket";
import { STUDIOS, type Studio } from "@/lib/cockpit-nav";

export type CockpitView = "workspace" | "history" | "setting";
export type OpenFile = { path: string; content: string; mime: string | null; dirty: boolean };
export type Entitlement = { marker: boolean };

export type CockpitContextValue = {
  // ---- state (spec §2.2) ----
  runId: string | null;
  view: CockpitView;
  activeStudio: Studio;
  manifest: Manifest | null;
  nodes: VfsNode[];
  openFile: OpenFile | null;
  entitlement: Entitlement;
  upsellOpen: boolean;
  // ---- actions ----
  startRun: (title?: string) => Promise<void>;
  openRun: (runId: string) => Promise<void>;
  refreshTree: () => Promise<void>;
  selectFile: (path: string) => Promise<void>;
  setOpenFileContent: (text: string) => void;
  closeFile: () => void;
  saveFile: () => Promise<void>;
  sendChat: (p: { prompt: string; provider: Provider; isMarker: boolean }) => Promise<void>;
  setStudio: (s: Studio) => void;
  setView: (v: CockpitView) => void;
  toggleEntitlement: () => Promise<void>;
  closeUpsell: () => void;
};

const CockpitContext = createContext<CockpitContextValue | null>(null);

/** VFS path 규칙: `/{runId}/{rest}`. rest = path 에서 접두 `/{runId}/` 제거. */
function restOf(runId: string, path: string): string {
  return path.replace(`/${runId}/`, "");
}

export function CockpitProvider({ children }: { children: React.ReactNode }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [view, setViewState] = useState<CockpitView>("workspace");
  const [activeStudio, setActiveStudio] = useState<Studio>(STUDIOS[0]);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [nodes, setNodes] = useState<VfsNode[]>([]);
  const [openFile, setOpenFile] = useState<OpenFile | null>(null);
  const [entitlement, setEntitlement] = useState<Entitlement>({ marker: false });
  const [upsellOpen, setUpsellOpen] = useState(false);

  // runId가 비동기 콜백(WS/poll) 안에서도 최신값을 가리키도록 ref 동기화.
  const runIdRef = useRef<string | null>(null);
  runIdRef.current = runId;

  /** `?run=` URL 쿼리를 현재 runId에 맞춘다(SSR 가드: effect/handler 안에서만 호출). */
  const syncRunQuery = useCallback((id: string | null) => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("run", id);
    else url.searchParams.delete("run");
    window.history.replaceState(null, "", url.toString());
  }, []);

  const refreshTree = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return;
    try {
      const { nodes: ns } = await api.vfsList(id);
      setNodes(ns);
    } catch {
      /* 트리 갱신 실패는 치명적이지 않음 — 다음 이벤트/폴에서 재시도 */
    }
  }, []);

  /** 기존 run 메타를 listRuns에서 찾아 manifest 채움(전용 manifest 엔드포인트 없음 — 계획서 §Task9 접근). */
  const loadManifest = useCallback(async (id: string) => {
    try {
      const { runs } = await api.listRuns();
      const m = runs.find((r) => r.run_id === id) ?? null;
      setManifest(m);
    } catch {
      setManifest(null);
    }
  }, []);

  const openRun = useCallback(
    async (id: string) => {
      setRunId(id);
      setActiveStudio(STUDIOS[0]);
      setViewState("workspace");
      setOpenFile(null);
      syncRunQuery(id);
      await Promise.all([loadManifest(id), api.vfsList(id).then(({ nodes: ns }) => setNodes(ns)).catch(() => setNodes([]))]);
    },
    [loadManifest, syncRunQuery],
  );

  const startRun = useCallback(
    async (title?: string) => {
      const { run_id } = await api.createRun(title);
      setRunId(run_id);
      setActiveStudio("brainstorming");
      setViewState("workspace");
      setManifest({ run_id, title: title ?? null, created_at: null, step_status: {} });
      setNodes([]);
      setOpenFile(null);
      syncRunQuery(run_id);
    },
    [syncRunQuery],
  );

  const selectFile = useCallback(async (path: string) => {
    const id = runIdRef.current;
    if (!id) return;
    const rest = restOf(id, path);
    const node = await api.vfsGet(id, rest);
    setOpenFile({ path, content: node.content_text ?? "", mime: node.mime, dirty: false });
  }, []);

  const setOpenFileContent = useCallback((text: string) => {
    setOpenFile((prev) => (prev ? { ...prev, content: text, dirty: true } : prev));
  }, []);

  const closeFile = useCallback(() => setOpenFile(null), []);

  const saveFile = useCallback(async () => {
    const id = runIdRef.current;
    if (!id || !openFile) return;
    const rest = restOf(id, openFile.path);
    await api.vfsPut(id, rest, openFile.content, openFile.mime ?? undefined);
    setOpenFile((prev) => (prev ? { ...prev, dirty: false } : prev));
    await refreshTree();
  }, [openFile, refreshTree]);

  const sendChat = useCallback(
    async (p: { prompt: string; provider: Provider; isMarker: boolean }) => {
      const id = runIdRef.current;
      if (!id) return;
      try {
        await api.gatewayRun({
          run_id: id,
          studio: activeStudio,
          prompt: p.prompt,
          provider: p.provider,
          is_marker: p.isMarker,
        });
        await refreshTree();
      } catch (e) {
        const status = (e as { status?: number }).status;
        if (status === 402) {
          setUpsellOpen(true);
          return;
        }
        throw e;
      }
    },
    [activeStudio, refreshTree],
  );

  const setStudio = useCallback((s: Studio) => setActiveStudio(s), []);
  const setView = useCallback((v: CockpitView) => setViewState(v), []);

  const toggleEntitlement = useCallback(async () => {
    const next = !entitlement.marker;
    const res = await api.setEntitlement(next);
    setEntitlement({ marker: res.marker });
  }, [entitlement.marker]);

  const closeUpsell = useCallback(() => setUpsellOpen(false), []);

  // ---- mount: `?run=` 복원 + entitlement 초기화 ----
  useEffect(() => {
    if (typeof window !== "undefined") {
      const fromUrl = new URL(window.location.href).searchParams.get("run");
      if (fromUrl) void openRun(fromUrl);
    }
    void api
      .getEntitlement()
      .then((e) => setEntitlement({ marker: e.marker }))
      .catch(() => {
        /* 백엔드 미기동 시 기본값(무료) 유지 */
      });
    // 마운트 시 1회만 실행 — openRun은 안정 콜백.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- WS: artifact/poll 수신 시 트리 재조회 ----
  useRunSocket(
    runId,
    (e) => {
      if (e.type === "artifact" || e.type === "poll") void refreshTree();
    },
    { pollMs: 4000 },
  );

  const value: CockpitContextValue = {
    runId,
    view,
    activeStudio,
    manifest,
    nodes,
    openFile,
    entitlement,
    upsellOpen,
    startRun,
    openRun,
    refreshTree,
    selectFile,
    setOpenFileContent,
    closeFile,
    saveFile,
    sendChat,
    setStudio,
    setView,
    toggleEntitlement,
    closeUpsell,
  };

  return <CockpitContext.Provider value={value}>{children}</CockpitContext.Provider>;
}

export function useCockpit(): CockpitContextValue {
  const ctx = useContext(CockpitContext);
  if (!ctx) throw new Error("useCockpit must be used within <CockpitProvider>");
  return ctx;
}
