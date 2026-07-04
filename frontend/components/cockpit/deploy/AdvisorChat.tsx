"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";

/** AdvisorChat (M6 T21) — 패키지 단위 advisor 챗. error 응답은 에러 말풍선으로 정직 표면
 *  (결제 표면 폐기 2026-07-04 — needsPayment/모달 경로 제거). */
type Message = { role: "user" | "assistant"; content: string };
type Props = {
  packageId: string;
  onSubmit: (message: string) => Promise<{ text?: string; tool_results?: unknown[]; error?: string }>;
};

export function AdvisorChat({ packageId, onSubmit }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    if (!input.trim() || sending) return;
    const userMsg = input;
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setInput("");
    setSending(true);
    try {
      const res = await onSubmit(userMsg);
      const content = res.error ? `⚠ ${res.error}` : (res.text ?? "(도구 실행 완료)");
      setMessages((m) => [...m, { role: "assistant", content }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="border border-outline-variant rounded p-3 flex flex-col gap-2" data-testid="advisor-chat">
      <div className="text-xs text-on-surface-variant">advisor · package={packageId}</div>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span className="inline-block px-2 py-1 rounded bg-surface-container-high text-body-sm">{m.content}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-1">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void send(); }}
          disabled={sending}
          className="flex-1 border border-outline-variant rounded px-2 text-sm disabled:opacity-60"
          data-testid="advisor-input"
        />
        <button
          type="button"
          onClick={send}
          disabled={sending}
          className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary text-on-primary rounded text-sm disabled:bg-surface-container disabled:text-on-surface-variant"
        >
          {sending && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
          {sending ? "처리 중" : "전송"}
        </button>
      </div>
    </div>
  );
}
