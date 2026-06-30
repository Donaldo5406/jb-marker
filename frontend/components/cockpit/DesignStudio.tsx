"use client";
import * as React from "react";
import { Group, Panel, Separator, useDefaultLayout } from "react-resizable-panels";
import { useCockpit } from "./CockpitProvider";
import { FileTree } from "./FileTree";
import { FileContent } from "./FileContent";
import { ChatPane } from "./ChatPane";
import { PipelineRail } from "./PipelineRail";
import { DesignSettings } from "./DesignSettings";
import { ConfirmToastView } from "./ConfirmToast";
import { AskUserToastView } from "./AskUserToast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AlertTriangle, X } from "lucide-react";

const LANGS = ["ko", "en", "vi", "zh"];

/** 리뷰 critical 후 디자인 복귀 시 '무엇을 고쳐야 하는지' 가이드 — review/report.md의
 *  R1 법률 검토 지적을 요약 카드로. 챗 교정(remediate) 안내까지 한 곳에 모은다. */
function ReviewGuideCard() {
  const c = useCockpit();
  const gate = c.reviewGate;
  const blocked = !!gate && gate.critical > 0;
  const [findings, setFindings] = React.useState<string[]>([]);
  React.useEffect(() => {
    if (!blocked || !c.runId) { setFindings([]); return; }
    let cancelled = false;
    void (async () => {
      try {
        const node = await api.vfsGet(c.runId!, "review/report.md");
        const lines = (node.content_text ?? "").split("\n");
        // "## R1 법률 검토" 섹션의 "- [severity] …" 항목만 추출(다음 ## 헤더에서 종료).
        const out: string[] = [];
        let inLegal = false;
        for (const ln of lines) {
          if (ln.startsWith("## R1")) { inLegal = true; continue; }
          if (inLegal && ln.startsWith("## ")) break;
          if (inLegal && ln.trim().startsWith("- ")) out.push(ln.trim().slice(2));
        }
        if (!cancelled) setFindings(out);
      } catch { if (!cancelled) setFindings([]); }
    })();
    return () => { cancelled = true; };
  }, [blocked, c.runId, gate?.critical, gate?.warning]);

  // 닫기(툴팁 dismiss) — 새 리뷰 결과(critical/warning 변화) 시 다시 노출.
  const [dismissed, setDismissed] = React.useState(false);
  React.useEffect(() => { setDismissed(false); }, [gate?.critical, gate?.warning]);

  if (!blocked || !gate || dismissed) return null;
  return (
    <div className="border-b border-severity-warning bg-severity-warning-bg px-4 py-2.5">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-severity-warning-fg" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-body-sm font-medium text-severity-warning-fg">
            리뷰에서 critical {gate.critical}건{gate.warning ? ` · warning ${gate.warning}건` : ""} — 카피를 교정해야 검토를 통과합니다.
          </p>
          {findings.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {findings.slice(0, 5).map((f, i) => (
                <li key={i} className="text-caption text-severity-warning-fg">· {f}</li>
              ))}
            </ul>
          )}
          <p className="mt-1.5 text-caption text-severity-warning-fg">
            우측 챗에 <span className="font-semibold">“리뷰 결과대로 카피 수정해줘”</span>라고 입력하면 카피가 자동 교정되고 캔버스가 갱신됩니다.
          </p>
        </div>
        <button type="button" onClick={() => setDismissed(true)} aria-label="가이드 닫기"
          className="shrink-0 rounded-full p-0.5 text-severity-warning-fg transition-opacity hover:opacity-70">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </div>
  );
}

/** design 탭: 상단 PipelineRail + 하단 4-panel(VFS·캔버스·미사용 안내·챗).
 *  VFS·챗 Panel은 collapsible. 캔버스 영역은 DesignEditor(자체 인스펙터/툴바)를 렌더. */
export function DesignStudio() {
  const c = useCockpit();
  const [busy, setBusy] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const act = async (action: string) => { setBusy(true); try { await c.runDesign(action); } finally { setBusy(false); } };
  const sceneOpen = !!c.openFile && c.openFile.path.endsWith(".scene");
  // brainstorming 확정 후 design 첫 진입(아직 S0=미시작)이면 중앙 모달로 셋업 시작을 권유 —
  // plan.md를 읽어 파이프라인(S0~Final)을 시작한다(첫 advance). '나중에'면 그 세션 동안 숨김.
  const [setupDismissed, setSetupDismissed] = React.useState(false);
  const setupOpen = c.manifest?.step_status?.brainstorming === "done"
    && c.designStep === "S0" && !busy && !setupDismissed;
  const layoutStorage = React.useMemo(
    () => (typeof window !== "undefined" ? window.localStorage : { getItem: () => null, setItem: () => {} }), []);
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id: "cockpit-cols-design", storage: layoutStorage });

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-surface">
      <PipelineRail step={c.designStep} gate={c.designGate} busy={busy}
        onAdvance={() => act("advance")} onRegenerate={() => act("regenerate")}
        settingsOpen={showSettings} onToggleSettings={() => setShowSettings((v) => !v)} />
      {showSettings && (
        <div className="border-b border-outline-variant bg-surface-container-low">
          <DesignSettings bypass={c.designBypass} onToggle={c.setDesignBypass} />
        </div>
      )}
      <ReviewGuideCard />
      <Group orientation="horizontal" defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged}
        className="min-h-0 flex-1 overflow-hidden">
        <Panel id="design-vfs" collapsible defaultSize={16} minSize={10} collapsedSize={3}
          className="min-h-0 overflow-hidden border-r border-outline-variant">
          <FileTree />
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="design-canvas" defaultSize={60} minSize={36} className="min-h-0 overflow-hidden">
          {sceneOpen && c.openFile ? (
            <FileContent file={c.openFile} runId={c.runId} onChangeContent={c.setOpenFileContent} onSaveScene={c.saveSceneJson} />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
              <p className="text-body-lg font-medium text-on-surface">디자인 캔버스</p>
              <p className="max-w-sm text-body-sm text-on-surface-variant">
                Final 단계에서 씬이 생성되면 여기서 직접 편집할 수 있습니다. 우측 챗으로 지시하거나 좌측 트리에서 main.scene을 선택하세요.
              </p>
            </div>
          )}
        </Panel>
        <Separator className="w-px bg-outline-variant data-[separator=hover]:bg-on-surface-variant data-[separator=active]:bg-on-surface-variant" />
        <Panel id="design-chat" collapsible defaultSize={24} minSize={16} collapsedSize={3}
          className="min-h-0 overflow-hidden border-l border-outline-variant">
          <div className="flex h-full min-h-0 flex-col">
            <div className="flex items-center gap-1.5 border-b border-outline-variant bg-surface-container-low px-3 py-2">
              <span className="mr-1 text-caption text-on-surface-variant">언어</span>
              {LANGS.map((l) => (
                <button key={l} type="button" onClick={() => void c.switchDesignLang(l)}
                  className={cn("rounded-full px-2.5 py-1 text-caption", c.designLang === l ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-high")}>
                  {l}
                </button>
              ))}
            </div>
            <div className="min-h-0 flex-1 overflow-hidden"><ChatPane /></div>
          </div>
        </Panel>
      </Group>
      <ConfirmToastView open={c.regenConfirm.open}
        message="수동 편집한 씬이 있습니다. 재생성하면 편집 내용이 새 씬으로 대체됩니다. 계속할까요?"
        confirmLabel="재생성" cancelLabel="취소"
        onConfirm={c.regenConfirm.onConfirm} onCancel={c.regenConfirm.onCancel} />
      {/* 디자인 스튜디오 랜드 시(미시작) AskUser 훅과 동일한 하단 토스트로 셋업 시작을 권유.
          옵션 칩=시작, X(닫기)=나중에. 중앙 모달 대신 비차단 토스트(브레인스토밍 직후 막아서지 않음). */}
      <AskUserToastView
        ask={setupOpen ? {
          trigger: "a",
          question: "디자인 셋업을 시작할까요? 확정된 plan.md를 읽어 레이아웃·카피·비주얼을 생성합니다.",
          options: ["plan 읽기 시작"],
        } : null}
        onSelect={() => { setSetupDismissed(true); void act("advance"); }}
        onClose={() => setSetupDismissed(true)}
      />
    </div>
  );
}
