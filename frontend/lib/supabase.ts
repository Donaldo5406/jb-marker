import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/** url·anon이 모두 있고 url이 유효해야 client 생성. createClient는 잘못된 URL에
 *  즉시 throw하므로(빌드/프리렌더 중단 위험) try로 감싸 실패 시 로컬 모드(null)로 강등. */
function makeClient(): SupabaseClient | null {
  if (!url || !anon) return null;
  try {
    return createClient(url, anon, {
      auth: { persistSession: true, autoRefreshToken: true },
    });
  } catch {
    // 잘못된 NEXT_PUBLIC_SUPABASE_URL → Supabase 비활성(로컬 모드, user_id="demo")로 폴백.
    return null;
  }
}

export const supabase: SupabaseClient | null = makeClient();

/** 세션 없으면 익명 로그인 후 토큰 반환. client 없으면 null. */
export async function ensureSession(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  if (data.session) return data.session.access_token;
  const { data: anonData, error } = await supabase.auth.signInAnonymously();
  if (error) return null;
  return anonData.session?.access_token ?? null;
}

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
