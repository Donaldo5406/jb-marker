"use client";

import * as React from "react";
import { Loader2, Paperclip, SendHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCockpit } from "./CockpitProvider";
import { ModelSelector, MODELS, type ModelChoice } from "./ModelSelector";

type ChatMessage = { id: number; role: "user" | "assistant"; text: string };

/** 우측 패널: 챗 메시지 목록 + 입력 도크.
 *  전송 → sendChat({prompt, provider, isMarker}); studio는 Provider가 activeStudio로 주입. */
export function ChatPane() {
  const c = useCockpit();
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [input, setInput] = React.useState("");
  const [model, setModel] = React.useState<ModelChoice>(MODELS[1]); // 기본 Claude(무료)
  const [loading, setLoading] = React.useState(false);
  const idRef = React.useRef(0);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const prompt = input.trim();
    if (!prompt || loading) return;
    const userMsg: ChatMessage = { id: ++idRef.current, role: "user", text: prompt };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const ok = await c.sendChat({ prompt, provider: model.provider, isMarker: model.isMarker });
      // 게이트(402) 케이스: Provider가 upsellOpen만 켜고 false 반환 → 성공라인 대신 안내 표시.
      setMessages((prev) => [
        ...prev,
        ok
          ? {
              id: ++idRef.current,
              role: "assistant",
              text: `완료 — 산출물을 좌측 트리에서 확인하세요. (${model.label})`,
            }
          : {
              id: ++idRef.current,
              role: "assistant",
              text: "Pro 전용 기능입니다 — Setting에서 엔타이틀먼트를 토글하세요.",
            },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: ++idRef.current, role: "assistant", text: "전송에 실패했습니다. 잠시 후 다시 시도하세요." },
      ]);
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
      </div>

      {/* 메시지 목록 */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && !loading ? (
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
          messages.map((m) => (
            <div
              key={m.id}
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
                {m.text}
              </div>
            </div>
          ))
        )}
        {loading && (
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
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="메시지를 입력하세요… (Enter 전송, Shift+Enter 줄바꿈)"
            className="block w-full resize-none bg-transparent px-3 py-2.5 text-body-sm text-on-surface outline-none placeholder:text-outline"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2">
            <button
              type="button"
              disabled
              title="파일 첨부 (준비 중)"
              aria-label="파일 첨부 (준비 중)"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-outline opacity-50"
            >
              <Paperclip className="h-4 w-4" aria-hidden />
            </button>
            <div className="flex items-center gap-2">
              <ModelSelector value={model.id} onChange={setModel} />
              <button
                type="button"
                onClick={() => void send()}
                disabled={!input.trim() || loading}
                aria-label="전송"
                className={cn(
                  "inline-flex h-8 w-8 items-center justify-center rounded-full transition-colors",
                  "bg-primary text-on-primary hover:bg-primary-container",
                  "disabled:opacity-40 disabled:pointer-events-none",
                )}
              >
                {loading ? (
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
