"use client";

import * as React from "react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, authedFetch, type AskPayload, type Manifest, type Provider, type VfsNode } from "@/lib/api";
import { ensureSession } from "@/lib/supabase";
import { useRunSocket } from "@/lib/useRunSocket";
import { STUDIOS, type Studio } from "@/lib/cockpit-nav";
import { isImagePath } from "@/lib/fileType";
import { assembleScene, type LayoutSpec } from "@/lib/sceneAssembler";
import { renderAndUploadAll } from "@/lib/sceneRender";

const DEPLOY_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type CockpitView = "workspace" | "history" | "setting";

/** `?view=` 쿼리값을 안전한 CockpitView로 정규화. 화이트리스트 외/누락은 기본 workspace. */
export function viewFromSearch(search: string): CockpitView {
  const v = new URLSearchParams(search).get("view");
  return v === "history" || v === "setting" ? v : "workspace";
}

export type OpenFile = { path: string; content: string; mime: string | null; dirty: boolean };
export type Entitlement = { marker: boolean; deploy: boolean };
export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ReviewStage = "R0" | "R1" | "R2" | "R3" | "done";
export type ReviewGate = { status: string; critical: number; warning: number };
export type DesignGate = { step: string; critic: Record<string, unknown> | null; auto_advanced: string[] };
// M6 T19 deploy 상태 타입.
export type DeployStateLike = {
  step_status: string;
  selected_providers: string[];
  matrix: { channel: string; lang: string }[];
  dev_pass: boolean;
};
export type EligibilityResult = { total: number; eligible_count: number; excluded_count: number };
export type PackageInfo = { status: string; reason?: string };
export type AdvisorResult = { text?: string; tool_results?: unknown[]; needsPayment?: boolean };
export type DispatchResult = { needsPayment?: boolean; report_path?: string } & Record<string, unknown>;

export type CockpitContextValue = {
  // ---- state (spec §2.2) ----
  runId: string | null;
  view: CockpitView;
  activeStudio: Studio;
  manifest: Manifest | null;
  nodes: VfsNode[];
  openFile: OpenFile | null;
  loadingPath: string | null;          // 현재 fetch 중인 파일 path(즉각 active+스피너용)
  entitlement: Entitlement;
  upsellOpen: boolean;
  messages: ChatMessage[];
  pendingAsk: AskPayload | null;
  brainStage: string | null;          // _state.json.stage
  designStep: string;                 // "S0".."done"
  designLang: string;                 // 현재 편집 언어
  setDesignLang: (l: string) => void;
  switchDesignLang: (lang: string) => Promise<void>;   // 언어 전환 + 해당 언어 scene 재조립/열기(I4)
  designBypass: Record<string, boolean>;   // 단계별 confirm 게이트 bypass 선호
  setDesignBypass: (id: string, on: boolean) => void;
  designGate: DesignGate | null;          // meta.gate — 현재 confirm 게이트 상태(critic/auto_advanced)
  // ---- review state (M5 spec §8.3) ----
  reviewStage: ReviewStage | null;          // R0..done 진행 — gateway response.meta.step에서 복원
  reviewGate: ReviewGate | null;            // 통합 reconciler 산정 결과(critical/warning 수)
  reviewAcknowledged: boolean;              // WARN ack 클릭 시 true — deploy 게이트 해제 조건
  // ---- deploy state (M6 T19) ----
  deployState: DeployStateLike | null;
  eligibility: EligibilityResult | null;
  packages: Record<string, PackageInfo>;
  devPass: boolean;
  selectedProviders: string[];
  setSelectedProviders: (next: string[]) => void;
  // ---- actions ----
  startRun: (title?: string) => Promise<void>;
  openRun: (runId: string) => Promise<void>;
  refreshTree: () => Promise<void>;
  selectFile: (path: string) => Promise<void>;
  setOpenFileContent: (text: string) => void;
  closeFile: () => void;
  saveFile: () => Promise<void>;
  sendChat: (p: { prompt: string; provider: Provider; isMarker: boolean; bypass?: boolean })
    => Promise<{ text?: string; ask?: AskPayload | null } | null>;
  runDesign: (action: string, prompt?: string) => Promise<{ text: string }>;
  runReview: () => Promise<{ text: string }>;
  ackReview: () => Promise<void>;
  restartReview: () => Promise<void>;
  saveSceneJson: (content: string) => Promise<void>;
  answerAsk: (choice: string) => Promise<void>;
  closeAsk: () => void;
  setStudio: (s: Studio) => void;
  setView: (v: CockpitView) => void;
  selectedHistoryRun: string | null;
  viewHistoryDetail: (runId: string) => void;
  closeHistoryDetail: () => void;
  toggleEntitlement: () => Promise<void>;
  toggleDeploy: () => void;
  closeUpsell: () => void;
  // ---- deploy actions (M6 T19) ----
  setupDeploy: (selected: string[], languages: string[]) => Promise<{ matrix?: { channel: string; lang: string }[]; step_status?: string } & Record<string, unknown>>;
  runEligibility: () => Promise<EligibilityResult>;
  runPackagingCell: (channel: string, lang: string, originalCopy: string, visualPath: string) => Promise<{ package_id: string; status: string; reason?: string } & Record<string, unknown>>;
  askAdvisor: (packageId: string, message: string) => Promise<AdvisorResult>;
  dispatchConfirm: () => Promise<DispatchResult>;
  payDemo: () => Promise<{ dev_pass: boolean }>;
  // ---- mock(시연) 모드 ----
  mockMode: boolean;
  setMockMode: (on: boolean) => void;
};

const CockpitContext = createContext<CockpitContextValue | null>(null);

/** VFS path 규칙: `/{runId}/{rest}`. rest = path 에서 접두 `/{runId}/` 제거. */
function restOf(runId: string, path: string): string {
  return path.replace(`/${runId}/`, "");
}

/** vfsGet + 비-404 오류 시 1회 재시도. HF Space 콜드스타트/일시 블립으로 인한
 *  복원 실패(=대화 휘발 체감)를 완화한다. 404(미존재)는 재시도 무의미하므로 즉시 전파. */
async function vfsGetRetry(runId: string, rest: string): Promise<VfsNode> {
  try {
    return await api.vfsGet(runId, rest);
  } catch (e) {
    if ((e as { status?: number }).status === 404) throw e;
    return await api.vfsGet(runId, rest);
  }
}

export function CockpitProvider({ children, runId: initialRunId }: { children: React.ReactNode; runId?: string }) {
  const [runId, setRunId] = useState<string | null>(initialRunId ?? null);
  const [view, setViewState] = useState<CockpitView>("workspace");
  const [activeStudio, setActiveStudio] = useState<Studio>(STUDIOS[0]);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [nodes, setNodes] = useState<VfsNode[]>([]);
  const [openFile, setOpenFile] = useState<OpenFile | null>(null);
  const [loadingPath, setLoadingPath] = useState<string | null>(null);
  // 파일 내용 캐시(path→OpenFile). 재클릭/재방문 시 네트워크 왕복 생략(#3 딜레이 해소).
  // 무효화: 저장 시 해당 path 갱신, artifact 이벤트(백엔드 재생성) 시 해당 path/전체 제거.
  const fileCacheRef = useRef<Map<string, OpenFile>>(new Map());
  const [entitlement, setEntitlement] = useState<Entitlement>({ marker: false, deploy: false });
  const [upsellOpen, setUpsellOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingAsk, setPendingAsk] = useState<AskPayload | null>(null);
  const [brainStage, setBrainStage] = useState<string | null>(null);
  const [designStep, setDesignStep] = useState("S0");
  const [designLang, setDesignLang] = useState("ko");
  const [designBypass, setDesignBypassState] = useState<Record<string, boolean>>({});
  const [designGate, setDesignGate] = useState<DesignGate | null>(null);
  // M5: 검토 진행 단계·게이트·ack 플래그(메모리 상). 새 run 마다 R0/null/false로 리셋.
  const [reviewStage, setReviewStage] = useState<ReviewStage | null>(null);
  const [reviewGate, setReviewGate] = useState<ReviewGate | null>(null);
  const [reviewAcknowledged, setReviewAcknowledged] = useState(false);
  // M6 T19: deploy state — runId 전환 시 리셋(openRun/startRun).
  const [deployState, setDeployState] = useState<DeployStateLike | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [packages, setPackages] = useState<Record<string, PackageInfo>>({});
  const [devPass, setDevPass] = useState(false);
  // 발송 채널 선택 — DeployStudio 로컬 대신 provider 소유(리마운트 생존). run 전환 시에만 리셋.
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  // M7-B: history 목록 ↔ 상세 뷰 전환 — 선택된 run id(null=목록 표시).
  const [selectedHistoryRun, setSelectedHistoryRun] = useState<string | null>(null);
  // 시연용 Mock 모드 — 모든 백엔드 호출에 mock 플래그 동봉. ref로 콜백 재생성 없이 최신값 참조.
  const [mockMode, setMockModeState] = useState(false);
  const mockModeRef = useRef(false);
  mockModeRef.current = mockMode;
  const setMockMode = useCallback((on: boolean) => {
    setMockModeState(on);
    if (typeof window !== "undefined") window.localStorage.setItem("jbm_mock_mode", on ? "1" : "0");
  }, []);

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

  /** `?view=` URL 쿼리를 현재 view에 맞춘다(기본값 workspace는 쿼리 제거). SSR 가드. */
  const syncViewQuery = useCallback((v: CockpitView) => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (v === "workspace") url.searchParams.delete("view");
    else url.searchParams.set("view", v);
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

  /** brain 내부 상태(_messages/_state)를 서버에서 복원.
   *  404 = 아직 대화/상태 없음(정상) → 기본값으로. 그 외 오류(네트워크/서버) → 기존 값 보존
   *  (일시 오류로 대화가 통째로 비워지는 휘발을 막는다). 재시도는 vfsGetRetry가 1회 수행. */
  const loadBrainState = useCallback(async (id: string) => {
    try {
      const m = await vfsGetRetry(id, "brainstorming/_messages.json");
      setMessages(m.content_text ? JSON.parse(m.content_text) : []);
    } catch (e) {
      if ((e as { status?: number }).status === 404) setMessages([]);
    }
    try {
      const st = await vfsGetRetry(id, "brainstorming/_state.json");
      const parsed = st.content_text ? JSON.parse(st.content_text) : null;
      setBrainStage(parsed?.stage ?? null);
      setPendingAsk(parsed?.pending_ask ?? null);
    } catch (e) {
      if ((e as { status?: number }).status === 404) { setBrainStage(null); setPendingAsk(null); }
    }
  }, []);

  /** design 내부 상태(_state.json)를 서버에서 복원(I3). 없으면(미시작) 무시. */
  const loadDesignState = useCallback(async (id: string) => {
    try {
      const st = await api.vfsGet(id, "design/_state.json");
      const s = st.content_text ? JSON.parse(st.content_text) : {};
      if (typeof s.step === "string") setDesignStep(s.step);
      if (s.bypass && typeof s.bypass === "object") setDesignBypassState(s.bypass);
      if (Array.isArray(s.languages) && s.languages[0]) setDesignLang(s.languages[0]);
    } catch { /* design 미시작 — 기본값 유지 */ }
  }, []);

  const openRun = useCallback(
    async (id: string) => {
      setRunId(id);
      setActiveStudio(STUDIOS[0]);
      setViewState("workspace");
      setOpenFile(null);
      // run 전환 시 이전 run의 챗/stage를 즉시 비운다 — 복원이 일시 실패해도 다른 run의
      // 대화가 잘못 표시되지 않도록(loadBrainState는 일시 오류 시 기존 값을 보존하므로 선행 리셋 필요).
      setMessages([]); setBrainStage(null); setPendingAsk(null);
      // M5 spec §7.4: run 전환 시 review state 3 필드 리셋 — 이전 run의 stale ack가
      // T18 isDeployUnlocked를 거짓 해제하지 않도록.
      setReviewStage(null); setReviewGate(null); setReviewAcknowledged(false);
      setDesignGate(null);   // 새로 연 run은 stale design 게이트 없이 시작.
      // M6 T19: deploy state 리셋(이전 run 잔여 차단).
      setDeployState(null); setEligibility(null); setPackages({}); setDevPass(false); setSelectedProviders([]);
      syncRunQuery(id);
      await Promise.all([loadManifest(id), loadBrainState(id), loadDesignState(id),
        api.vfsList(id).then(({ nodes: ns }) => setNodes(ns)).catch(() => setNodes([]))]);
    },
    [loadManifest, loadBrainState, loadDesignState, syncRunQuery],
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
      setMessages([]); setPendingAsk(null); setBrainStage("A");
      setReviewStage(null); setReviewGate(null); setReviewAcknowledged(false);
      setDesignGate(null);   // 새 run은 stale design 게이트 없이 시작.
      setDeployState(null); setEligibility(null); setPackages({}); setDevPass(false); setSelectedProviders([]);
      syncRunQuery(run_id);
    },
    [syncRunQuery],
  );

  const selectFile = useCallback(async (path: string) => {
    const id = runIdRef.current;
    if (!id) return;
    // 캐시 히트 → 즉시 표시, 네트워크 생략.
    const cached = fileCacheRef.current.get(path);
    if (cached) {
      setOpenFile(cached);
      setLoadingPath(null);
      return;
    }
    // 이미지(PNG 등)는 raw 바이트로 서빙되어 vfsGet(res.json())이 깨진다("... is not valid JSON").
    // 텍스트 fetch를 건너뛰고 메타만 세팅 → EditorPane이 <ImageView>(useAuthedBlob)로 blob 표시.
    if (isImagePath(path)) {
      const of: OpenFile = { path, content: "", mime: null, dirty: false };
      fileCacheRef.current.set(path, of);
      setOpenFile(of);
      setLoadingPath(null);
      return;
    }
    // 캐시 미스 → 클릭 즉시 로딩 표시(낙관적 피드백) 후 fetch.
    setLoadingPath(path);
    try {
      const rest = restOf(id, path);
      const node = await api.vfsGet(id, rest);
      const of: OpenFile = { path, content: node.content_text ?? "", mime: node.mime, dirty: false };
      fileCacheRef.current.set(path, of);
      setOpenFile(of);
    } finally {
      // 다른 파일을 그 사이 클릭했다면(loadingPath 변경) 그 로딩은 유지.
      setLoadingPath((p) => (p === path ? null : p));
    }
  }, []);

  /** backend layout.spec → assembleScene → design/final/{lang}/main.scene 저장 후 에디터에 자동 open(C1).
   *  rough spec이 없으면(파이프라인 미완) no-op. 빈 spec({}) 이어도 빈 scene을 안전 생성. */
  const assembleAndOpenScene = useCallback(async (lang: string) => {
    const id = runIdRef.current;
    if (!id) return;
    let node;
    try { node = await api.vfsGet(id, "design/rough/layout.spec.json"); }
    catch { return; }                 // rough spec 없음 → 조립할 것 없음
    let spec: LayoutSpec;
    try { spec = JSON.parse(node.content_text ?? "{}"); }
    catch { return; }
    // 배경 슬롯을 S2a 생성 비주얼(고정 경로)에 연결.
    const VISUAL = "design-system/components/visual/v1.png";
    if (Array.isArray(spec?.slots)) {
      const bg = spec.slots.find((s) => s.role === "background");
      if (bg) bg.asset_ref = VISUAL;
    }
    const scene = assembleScene(spec, lang, (ref) => api.assetUrl(id, `design/${ref}`));
    await api.vfsPut(id, `design/final/${lang}/main.scene`, JSON.stringify(scene), "application/json");
    await refreshTree();
    await selectFile(`/${id}/design/final/${lang}/main.scene`);
  }, [refreshTree, selectFile]);

  const setOpenFileContent = useCallback((text: string) => {
    setOpenFile((prev) => (prev ? { ...prev, content: text, dirty: true } : prev));
  }, []);

  const closeFile = useCallback(() => setOpenFile(null), []);

  const saveFile = useCallback(async () => {
    const id = runIdRef.current;
    if (!id || !openFile) return;
    const rest = restOf(id, openFile.path);
    await api.vfsPut(id, rest, openFile.content, openFile.mime ?? undefined);
    const saved: OpenFile = { ...openFile, dirty: false };
    fileCacheRef.current.set(openFile.path, saved);   // 캐시 동기화(저장 내용 = 서버 최신).
    setOpenFile(saved);
    await refreshTree();
  }, [openFile, refreshTree]);

  const sendChat = useCallback(
    async (p: { prompt: string; provider: Provider; isMarker: boolean; bypass?: boolean }) => {
      const id = runIdRef.current;
      if (!id) return null;
      setMessages((m) => [...m, { role: "user", content: p.prompt }]);
      try {
        const res = await api.gatewayRun({
          run_id: id, studio: activeStudio, prompt: p.prompt,
          provider: p.provider, is_marker: p.isMarker, bypass: p.bypass ?? false,
          mock: mockModeRef.current,
        });
        if (res.text) setMessages((m) => [...m, { role: "assistant", content: res.text }]);
        setPendingAsk(res.ask ?? null);
        // loadManifest: step_status 변경(D8 done→design 활성)을 ProcessBar에 세션 내 반영.
        await Promise.all([refreshTree(), loadBrainState(id), loadManifest(id)]);
        return { text: res.text, ask: res.ask ?? null };
      } catch (e) {
        const status = (e as { status?: number }).status;
        if (status === 402) { setUpsellOpen(true); return null; }
        throw e;
      }
    },
    [activeStudio, refreshTree, loadBrainState, loadManifest],
  );

  /** design 파이프라인 1턴 — gateway(studio="design", is_marker, action) 호출 후
   *  트리 갱신 + 응답 meta.step으로 designStep 추적. provider는 brain과 동일하게 anthropic 기본. */
  const runDesign = useCallback(async (action: string, prompt = "") => {
    const id = runIdRef.current;
    if (!id) return { text: "" };
    const res = await api.gatewayRun({
      run_id: id, studio: "design", prompt,
      provider: "anthropic", is_marker: true, action,
      bypass: !!designBypass[designStep],   // 호환: 현재 step의 bypass 단일 플래그
      bypass_map: designBypass,             // 전체 맵 전송(백엔드 연쇄 전제)
      mock: mockModeRef.current,
    });
    await refreshTree();
    const st = res.meta?.step;
    if (typeof st === "string") setDesignStep(st);
    setDesignGate((res.meta?.gate as DesignGate) ?? null);   // 게이트 상태 보존(meta.gate)
    // S3→done: 백엔드 layout.spec 완성 → 현재 언어 scene 조립 + 자동 open(C1).
    if (st === "done") await assembleAndOpenScene(designLang);
    return { text: res.text };
  }, [refreshTree, designBypass, designStep, assembleAndOpenScene, designLang]);

  const setDesignBypass = useCallback(
    (id: string, on: boolean) => setDesignBypassState((m) => ({ ...m, [id]: on })),
    [],
  );

  /** 검토 시작/계속(spec §8.3): composite PNG 업로드 후 백엔드 상태머신을 done까지 순차 완주.
   *  백엔드 review는 gateway 호출 1번당 한 단계(R0→R1→R2→R3)만 전진하므로, 한 번의 사용자
   *  액션으로 끝까지 돌도록 done(=R3 실행)까지 루프한다. 중간 단계에서 호출해도 백엔드 현재
   *  step부터 이어서 완주(복구·resume). 각 단계 산출물은 refreshTree로 즉시 트리에 반영.
   *  성공한 lang만 vision 입력으로 사용(renderAndUploadAll graceful skip). */
  const runReview = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return { text: "" };
    // 1) 모든 final/{lang}/main.scene 로드 — vfsList로 lang 탐색.
    const scenes: Record<string, any> = {};
    try {
      const { nodes: ns } = await api.vfsList(id);
      const sceneNodes = ns.filter((n) => /^design\/final\/[^/]+\/main\.scene$/.test(n.path));
      for (const n of sceneNodes) {
        const m = n.path.match(/^design\/final\/([^/]+)\/main\.scene$/);
        const lang = m?.[1];
        if (!lang) continue;
        try {
          const node = await api.vfsGet(id, n.path);
          scenes[lang] = node.content_text ? JSON.parse(node.content_text) : {};
        } catch { /* lang 누락 — graceful skip */ }
      }
    } catch { /* vfsList 실패 → 빈 scenes로 진입(백엔드는 vision_skipped로 흡수) */ }
    // 2) composite PNG 업로드 (lib/sceneRender — base64 round-trip, /api/vfs/.../review/_render/{lang}.png).
    await renderAndUploadAll(id, scenes);
    // 3) R0→R3 순차 구동. STEP_GUARD = 정상 4단계 + 여유(무한루프 방지 안전캡).
    const STEP_GUARD = 6;
    const nextStage = (st: string): ReviewStage =>
      st === "R0" ? "R1" : st === "R1" ? "R2" : "R3";
    let lastText = "";
    let gate: any = null;
    for (let i = 0; i < STEP_GUARD; i++) {
      const res = await api.gatewayRun({
        run_id: id, studio: "review", prompt: i === 0 ? "검토 시작" : "계속",
        provider: "anthropic", is_marker: true, mock: mockModeRef.current,
      });
      lastText = res.text ?? lastText;
      const g = (res.meta as any)?.gate;
      if (g && typeof g === "object") gate = g;
      await refreshTree();                       // 단계 산출물(legal/·i18n/·report.md) 즉시 반영
      const st = res.meta?.step;
      if (st === "R3") { setReviewStage("done"); break; }   // R3=종단(state→done)
      setReviewStage(nextStage(typeof st === "string" ? st : "R0"));   // 진행 표시
    }
    // 4) 게이트·manifest 반영.
    if (gate) {
      setReviewGate({
        status: String(gate.status ?? ""),
        critical: Number(gate.critical ?? 0),
        warning: Number(gate.warning ?? 0),
      });
    }
    await loadManifest(id);
    return { text: lastText };
  }, [refreshTree, loadManifest]);

  /** WARN ack(spec §8.3): backend acknowledged flag 갱신 + 클라이언트 플래그 set. */
  const ackReview = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return;
    await api.gatewayRun({
      run_id: id, studio: "review", prompt: "",
      provider: "anthropic", is_marker: true, action: "ack", mock: mockModeRef.current,
    });
    setReviewAcknowledged(true);
    await loadManifest(id);
  }, [loadManifest]);

  /** 재검토(spec §8.3): backend signal 초기화 + 클라이언트 상태 리셋. */
  const restartReview = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return;
    await api.gatewayRun({
      run_id: id, studio: "review", prompt: "",
      provider: "anthropic", is_marker: true, action: "restart", mock: mockModeRef.current,
    });
    setReviewStage("R0");
    setReviewGate(null);
    setReviewAcknowledged(false);
    await Promise.all([refreshTree(), loadManifest(id)]);
  }, [refreshTree, loadManifest]);

  /** 언어 전환(I4): 현재 언어를 바꾸고 해당 언어 scene을 재조립/열기(spec 없으면 no-op). */
  const switchDesignLang = useCallback(async (lang: string) => {
    setDesignLang(lang);
    await assembleAndOpenScene(lang);
  }, [assembleAndOpenScene]);

  /** 캔버스 편집 결과(scene JSON)를 현재 열린 .scene 파일에 in-place 저장. */
  const saveSceneJson = useCallback(async (content: string) => {
    const id = runIdRef.current;
    if (!id || !openFile) return;
    const rest = restOf(id, openFile.path);
    await api.vfsPut(id, rest, content, "application/json");
    // 캔버스 저장 결과를 캐시에 반영(다음 selectFile이 stale 내용을 돌려주지 않도록).
    fileCacheRef.current.set(openFile.path, { ...openFile, content, dirty: false });
  }, [openFile]);

  const answerAsk = useCallback(async (choice: string) => {
    const id = runIdRef.current;
    if (!id || !pendingAsk) return;
    setMessages((m) => [...m, { role: "user", content: choice }]);
    setPendingAsk(null);
    try {
      const res = await api.gatewayRun({
        run_id: id, studio: "brainstorming", prompt: choice,
        provider: "anthropic", is_marker: true, answer: choice, mock: mockModeRef.current,
      });
      if (res.text) setMessages((m) => [...m, { role: "assistant", content: res.text }]);
      setPendingAsk(res.ask ?? null);
      // loadManifest: plan-lock(D8 done)이 ProcessBar/design 활성에 세션 내 반영되도록.
      await Promise.all([refreshTree(), loadBrainState(id), loadManifest(id)]);
    } catch (e) {
      const status = (e as { status?: number }).status;
      if (status === 402) setUpsellOpen(true);
    }
  }, [pendingAsk, refreshTree, loadBrainState, loadManifest]);

  const closeAsk = useCallback(() => setPendingAsk(null), []);

  const setStudio = useCallback((s: Studio) => setActiveStudio(s), []);
  const setView = useCallback(
    (v: CockpitView) => {
      setViewState(v);
      syncViewQuery(v);
    },
    [syncViewQuery],
  );
  const viewHistoryDetail = useCallback((id: string) => setSelectedHistoryRun(id), []);
  const closeHistoryDetail = useCallback(() => setSelectedHistoryRun(null), []);

  const toggleEntitlement = useCallback(async () => {
    const next = !entitlement.marker;
    const res = await api.setEntitlement(next);
    setEntitlement((e) => ({ ...e, marker: res.marker }));
  }, [entitlement.marker]);

  // deploy 엔타이틀먼트는 데모 클라이언트 플래그(stub 결제) — 라이브 Supabase 스키마 무변경.
  const toggleDeploy = useCallback(() => {
    setEntitlement((e) => {
      const nd = !e.deploy;
      if (typeof window !== "undefined") window.localStorage.setItem("jbm_deploy_entitlement", nd ? "1" : "0");
      return { ...e, deploy: nd };
    });
  }, []);

  const closeUpsell = useCallback(() => setUpsellOpen(false), []);

  // ---- M6 T19: deploy 액션 6개 ----
  // 모든 액션은 runIdRef.current를 통해 최신 runId를 사용한다(WS/poll 콜백과 동일 패턴).
  // /runs/... 경로는 NEXT_PUBLIC_API_BASE로 직접 호출(api.ts와 일관, 로컬·Vercel 공용).
  const setupDeploy = useCallback(async (selected: string[], languages: string[]) => {
    const id = runIdRef.current;
    if (!id) return {} as { matrix?: { channel: string; lang: string }[]; step_status?: string };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_providers: selected, languages }),
    });
    const data = await res.json();
    // 응답으로 deploy 상태 동기화(이전: 미갱신 버그). 선택값은 인자를 권위로 보존.
    setDeployState((prev) => ({
      step_status: typeof data.step_status === "string" ? data.step_status : prev?.step_status ?? "in_progress",
      selected_providers: selected,
      matrix: Array.isArray(data.matrix) ? data.matrix : [],
      dev_pass: prev?.dev_pass ?? false,
    }));
    return data;
  }, []);

  const runEligibility = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return { total: 0, eligible_count: 0, excluded_count: 0 };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/eligibility`, { method: "POST" });
    const data = await res.json();
    setEligibility(data);
    return data;
  }, []);

  const runPackagingCell = useCallback(async (channel: string, lang: string, originalCopy: string, visualPath: string) => {
    const id = runIdRef.current;
    if (!id) return { package_id: `${channel}_${lang}`, status: "error" };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/packages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, lang, original_copy: originalCopy, visual_path: visualPath }),
    });
    const data = await res.json();
    if (data && data.package_id) {
      setPackages((p) => ({ ...p, [data.package_id]: { status: data.status, reason: data.reason } }));
    }
    return data;
  }, []);

  const askAdvisor = useCallback(async (packageId: string, message: string): Promise<AdvisorResult> => {
    const id = runIdRef.current;
    if (!id) return { needsPayment: false };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/advisor/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ package_id: packageId, message, mock: mockModeRef.current }),
    });
    if (res.status === 402) {
      return { needsPayment: true };
    }
    return res.json();
  }, []);

  const dispatchConfirm = useCallback(async (): Promise<DispatchResult> => {
    const id = runIdRef.current;
    if (!id) return { needsPayment: false };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmed: true }),
    });
    if (res.status === 402) {
      return { needsPayment: true };
    }
    return res.json();
  }, []);

  const payDemo = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return { dev_pass: false };
    const res = await authedFetch(`${DEPLOY_BASE}/runs/${id}/deploy/demo-payment`, { method: "POST" });
    const data = await res.json();
    setDevPass(!!data.dev_pass);
    return data;
  }, []);

  // `?view=` 딥링크 복원 — ensureSession과 독립적으로 즉시 1회(예: /cockpit?view=history).
  // 초기 렌더는 workspace, 마운트 직후 effect로 교정(하이드레이션 불일치 회피, `?run=` 복원과 동일 패턴).
  useEffect(() => {
    if (typeof window === "undefined") return;
    setViewState(viewFromSearch(window.location.search));
    // 마운트 1회만(의존: 모듈 스코프 viewFromSearch + 안정 setter setViewState → exhaustive-deps 미발화).
  }, []);

  // ---- mount: 익명 세션 확보 → `?run=` 복원 + entitlement 초기화 ----
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      // 익명 세션을 먼저 확보해야 이후 authed 호출(listRuns 등)에 토큰이 붙는다.
      // 로컬 모드(Supabase 미설정)에선 ensureSession이 즉시 null → 기존 흐름 유지.
      await ensureSession();
      if (cancelled) return;
      if (typeof window !== "undefined") {
        const mm = window.localStorage.getItem("jbm_mock_mode");
        if (mm !== null) setMockModeState(mm === "1");
        const fromUrl = new URL(window.location.href).searchParams.get("run");
        if (fromUrl) void openRun(fromUrl);
        const dep = window.localStorage.getItem("jbm_deploy_entitlement") === "1";
        setEntitlement((e) => ({ ...e, deploy: dep }));
      }
      void api
        .getEntitlement()
        .then((e) => setEntitlement((prev) => ({ ...prev, marker: e.marker })))
        .catch(() => {
          /* 백엔드 미기동 시 기본값(무료) 유지 */
        });
    })();
    return () => { cancelled = true; };
    // 마운트 시 1회만 실행 — openRun은 안정 콜백.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- WS: askuser → pendingAsk, artifact/poll → 트리 재조회 ----
  // artifact(백엔드 쓰기)는 캐시 무효화도 수행 — 재생성된 파일이 stale 캐시로 가려지지 않도록.
  // poll(쓰기 아님)은 트리만 갱신해 캐시를 보존(#3 딜레이 해소 핵심).
  useRunSocket(runId, (e) => {
    if (e.type === "askuser" && e.ask) {
      setPendingAsk(e.ask);
    } else if (e.type === "artifact") {
      if (e.path) {
        fileCacheRef.current.delete(e.path);
        // 현재 열린 파일이 재생성됐으면 새 내용으로 다시 연다.
        if (openFile?.path === e.path) void selectFile(e.path);
      } else {
        fileCacheRef.current.clear();
      }
      void refreshTree();
    } else if (e.type === "poll") {
      void refreshTree();
    }
  }, { pollMs: 4000 });

  const value: CockpitContextValue = {
    runId,
    view,
    activeStudio,
    manifest,
    nodes,
    openFile,
    loadingPath,
    entitlement,
    upsellOpen,
    messages,
    pendingAsk,
    brainStage,
    designStep,
    designLang,
    setDesignLang,
    switchDesignLang,
    designBypass,
    setDesignBypass,
    designGate,
    reviewStage,
    reviewGate,
    reviewAcknowledged,
    deployState,
    eligibility,
    packages,
    devPass,
    selectedProviders,
    setSelectedProviders,
    startRun,
    openRun,
    refreshTree,
    selectFile,
    setOpenFileContent,
    closeFile,
    saveFile,
    sendChat,
    runDesign,
    runReview,
    ackReview,
    restartReview,
    saveSceneJson,
    answerAsk,
    closeAsk,
    setStudio,
    setView,
    selectedHistoryRun,
    viewHistoryDetail,
    closeHistoryDetail,
    toggleEntitlement,
    toggleDeploy,
    closeUpsell,
    setupDeploy,
    runEligibility,
    runPackagingCell,
    askAdvisor,
    dispatchConfirm,
    payDemo,
    mockMode,
    setMockMode,
  };

  return <CockpitContext.Provider value={value}>{children}</CockpitContext.Provider>;
}

export function useCockpit(): CockpitContextValue {
  const ctx = useContext(CockpitContext);
  if (!ctx) throw new Error("useCockpit must be used within <CockpitProvider>");
  return ctx;
}
