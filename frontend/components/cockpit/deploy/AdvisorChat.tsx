"use client";
import { useState } from "react";

/** AdvisorChat (M6 T21) — 패키지 단위 advisor 챗. needsPayment 응답 시 onPayDemo로 모달 트리거. */
type Message = { role: "user" | "assistant"; content: string };
type Props = {
  packageId: string;
  onSubmit: (message: string) => Promise<{ text?: string; tool_results?: unknown[]; needsPayment?: boolean }>;
  onPayDemo: () => void;
};

export function AdvisorChat({ packageId, onSubmit, onPayDemo }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  async function send() {
    if (!input.trim()) return;
    const userMsg = input;
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setInput("");
    const res = await onSubmit(userMsg);
    if (res.needsPayment) {
      onPayDemo();
      return;
    }
    setMessages((m) => [...m, { role: "assistant", content: res.text ?? "(도구 실행 완료)" }]);
  }

  return (
    <div className="border border-outline-variant rounded p-3 flex flex-col gap-2" data-testid="advisor-chat">
      <div className="text-xs text-on-surface-variant">advisor · package={packageId}</div>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span className="inline-block px-2 py-1 rounded bg-surface-container-high text-sm">{m.content}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-1">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 border border-outline-variant rounded px-2 text-sm"
          data-testid="advisor-input"
        />
        <button
          type="button"
          onClick={send}
          className="px-3 py-1 bg-primary text-on-primary rounded text-sm"
        >
          전송
        </button>
      </div>
    </div>
  );
}
