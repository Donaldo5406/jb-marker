"use client";

import * as React from "react";
import { supabase } from "@/lib/supabase";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export function AccountPanel() {
  const [email, setEmail] = React.useState<string | null>(null);
  const [isAnon, setIsAnon] = React.useState(true);
  const [input, setInput] = React.useState("");
  const [msg, setMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
      setIsAnon(Boolean(data.user?.is_anonymous));
    });
  }, []);

  if (!supabase) {
    return (
      <Card className="p-6 text-body-sm text-on-surface-variant">
        Supabase 미설정(로컬 모드) — 게스트(demo)로 동작합니다.
      </Card>
    );
  }

  // 위 가드 이후 non-null이지만, TS는 import 바인딩을 클로저 안에서 좁히지 못한다 → 로컬 const로 고정.
  const sb = supabase;

  const upgrade = async () => {
    setMsg(null);
    const { error } = await sb.auth.updateUser({ email: input });
    setMsg(error ? `실패: ${error.message}` : "확인 메일을 보냈습니다. 메일의 링크로 인증하세요.");
  };

  const signOut = async () => {
    await sb.auth.signOut();
    window.location.reload();
  };

  return (
    <Card className="space-y-4 p-6">
      <div>
        <h2 className="text-h3 text-on-surface">계정</h2>
        <p className="text-body-sm text-on-surface-variant">
          {email ? `로그인: ${email}` : isAnon ? "게스트 세션 (익명)" : "로그인됨"}
        </p>
      </div>
      {isAnon && (
        <div className="space-y-2">
          <p className="text-body-sm text-on-surface-variant">
            이메일을 연결하면 다른 기기에서도 작업을 이어갈 수 있습니다.
          </p>
          <div className="flex gap-2">
            <input
              type="email"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="you@example.com"
              className="flex-1 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-sm"
            />
            <Button size="sm" onClick={() => void upgrade()} disabled={!input}>
              이메일 연결
            </Button>
          </div>
          {msg && <p className="text-caption text-on-surface-variant">{msg}</p>}
        </div>
      )}
      <Button variant="secondary" size="sm" onClick={() => void signOut()}>
        로그아웃
      </Button>
    </Card>
  );
}
