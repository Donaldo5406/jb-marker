"use client";

import * as React from "react";
import { Loader2, SendHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";
import { ModelSelector, MODELS, type ModelChoice } from "./ModelSelector";

// 마지막 선택 모델 — 스튜디오 전환으로 ChatPane이 재마운트돼도 유지(모듈 수명).
// 기본값 = Marker(Pro): 데모 본선 피드백(2026-07-05) — 매 뷰 전환마다 Claude로
// 리셋되면 발표자가 재선택을 잊어 일반 어시스턴트로 빠지는 함정이 있었다.
let lastModel: ModelChoice = MODELS[0];

/** 우측 패널: 챗 메시지 목록 + 입력 도크.
 *  대화는 Provider(c.messages)가 소유·복원. 전송 → sendChat({prompt, provider, isMarker}).
 *  402/업셀은 Provider가 처리(null 반환 + upsell). Stage 배지는 c.brainStage로 표시. */
export function ChatPane() {
  const c = useCockpit();
  const [input, setInput] = React.useState("");
  const [model, setModelState] = React.useState<ModelChoice>(lastModel);
  const setModel = React.useCallback((m: ModelChoice) => {
    lastModel = m;
    setModelState(m);
  }, []);
  const [loading, setLoading] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  // 로컬 전송(loading) + AskUserToast 선택 등 Provider 경로(c.chatPending)를 합친 응답 대기 상태.
  // '생성 중…' 인디케이터·입력 잠금·스크롤 트리거가 두 경로 모두에서 동일하게 동작.
  const busy = loading || c.chatPending;

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [c.messages, busy]);

  // AskUserToast '채팅으로 답하기' 등 외부 포커스 요청 — nonce 증가 시 입력에 포커스(초기 0은 무시).
  React.useEffect(() => {
    if (c.chatFocusNonce > 0) inputRef.current?.focus();
  }, [c.chatFocusNonce]);

  const send = async () => {
    const prompt = input.trim();
    if (!prompt || busy) return;
    setInput("");
    setLoading(true);
    try {
      // 브레인스토밍 bypass는 제거됨 — spec/plan 확정은 항상 AI가 사용자에게 묻는다(단계 전환 통제).
      await c.sendChat({ prompt, provider: model.provider, isMarker: model.isMarker });
    } catch (err) {
      // 402(업셀)는 Provider가 처리. 그 외(네트워크/500)는 unhandled rejection 방지용 로깅.
      console.error("sendChat failed", err);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface-container-low">
      <div className="flex items-center gap-2 border-b border-outline-variant px-4 py-2.5">
        <Sparkles className="h-4 w-4 text-primary" aria-hidden />
        <span className="text-body-sm font-medium text-on-surface">AI 챗</span>
        <div className="ml-auto flex items-center gap-2">
          {c.activeStudio === "brainstorming" && (
            <div className="flex items-center gap-0.5 rounded-full bg-surface-container-high p-0.5">
              {([["image", "이미지"], ["video", "영상"]] as const).map(([m, label]) => (
                <button key={m} type="button" data-testid={`medium-${m}`}
                  onClick={() => c.setVideoMedium(m)}
                  className={cn("rounded-full px-2.5 py-0.5 text-caption",
                    c.videoMedium === m ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-surface-container-highest")}>
                  {label}
                </button>
              ))}
            </div>
          )}
          {c.brainStage && (
            <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-caption text-on-surface-variant">
              {c.brainStage === "A" ? "Stage A · 탐색" : c.brainStage === "B" ? "Stage B · 계획" : "완료"}
            </span>
          )}
        </div>
      </div>

      {/* 메시지 목록 */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {c.messages.length === 0 && !busy ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-container-high">
              <Sparkles className="h-5 w-5 text-primary" aria-hidden />
            </div>
            <p className="text-body-sm font-medium text-on-surface">무엇을 만들까요?</p>
            <p className="text-caption text-on-surface-variant">
              프롬프트를 입력하면 산출물이 좌측 트리에 생성됩니다
            </p>
          </div>
        ) : (
          c.messages.map((m, i) => (
            <div
              key={i}
              className={cn("flex animate-fade-in-up", m.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-body-sm",
                  m.role === "user"
                    ? "rounded-br-sm bg-primary text-on-primary"
                    : "rounded-bl-sm border border-outline-variant bg-surface-container-lowest text-on-surface",
                )}
              >
                {m.content}
              </div>
            </div>
          ))
        )}
        {busy && (
          <div className="flex justify-start animate-fade-in-up">
            <div className="inline-flex items-center gap-2 rounded-2xl rounded-bl-sm border border-outline-variant bg-surface-container-lowest px-3.5 py-2 text-body-sm text-on-surface-variant">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              생성 중…
            </div>
          </div>
        )}
      </div>

      {/* 입력 도크 */}
      <div className="border-t border-outline-variant bg-surface-container-low p-3">
        <div className="rounded-xl border border-outline-variant bg-surface-container-lowest focus-within:ring-1 focus-within:ring-primary">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="메시지를 입력하세요… (Enter 전송, Shift+Enter 줄바꿈)"
            className="block w-full resize-none bg-transparent px-3 py-2.5 text-body-sm text-on-surface outline-none placeholder:text-outline"
          />
          <div className="flex items-center justify-end gap-2 px-2 pb-2">
            <div className="flex items-center gap-2">
              <ModelSelector value={model.id} onChange={setModel} />
              <button
                type="button"
                onClick={() => void send()}
                disabled={!input.trim() || busy}
                aria-label="전송"
                className={cn(
                  "inline-flex h-8 w-8 items-center justify-center rounded-full transition-colors",
                  "bg-primary text-on-primary hover:bg-primary-container",
                  "disabled:opacity-40 disabled:pointer-events-none",
                )}
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <SendHorizontal className="h-4 w-4" aria-hidden />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
