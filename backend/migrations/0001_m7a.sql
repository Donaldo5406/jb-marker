-- backend/migrations/0001_m7a.sql
-- M7-A: runs / vfs_nodes / profiles + RLS. Supabase SQL 에디터에서 1회 실행.
--
-- 설계 메모(0001_init.sql 대비 의도된 차이):
--  · user_id 는 text 유지(0001_init.sql 과 일치). 백엔드가 JWT sub(uuid 문자열)을
--    그대로 저장하고, 로컬-우선 폴백 'demo' 도 담아야 하므로 uuid 컬럼 대신 text.
--  · 접근 A(백엔드 강제): 백엔드는 service_role 로 RLS 를 우회하고 소유권은
--    require_run_owner 가드가 코드로 강제. RLS 는 anon 직접 접근을 막는 방어선일 뿐.
--    따라서 정책은 auth.uid()::text = user_id 로 타입을 맞춘다.
--  · 멱등/비파괴: 전부 if not exists / drop ... if exists 로 재실행 안전.
--    0001_init.sql 이 이미 적용됐어도(=FK 가 cascade 없이 존재) 아래에서 보정한다.

-- 1) 테이블 (init 미적용 시 신규 생성)
create table if not exists runs (
  run_id       text primary key,
  user_id      text not null default 'demo',
  title        text,
  current_step text,
  step_status  jsonb not null default '{}',
  languages    text[] not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create table if not exists vfs_nodes (
  run_id       text not null,
  path         text not null,
  kind         text,
  mime         text,
  source       text,
  content_text text,
  blob_path    text,
  meta         jsonb not null default '{}',
  grounds      jsonb,
  hash         text,
  created_at   timestamptz not null default now(),
  primary key (run_id, path)
);

create table if not exists profiles (
  user_id    text primary key,
  entitled   boolean not null default false,
  created_at timestamptz not null default now()
);

-- 2) FK 를 on delete cascade 로 보정 (init 의 cascade 없는 FK 도 교체 → run 삭제 시 노드 정리)
alter table vfs_nodes drop constraint if exists vfs_nodes_run_id_fkey;
alter table vfs_nodes
  add constraint vfs_nodes_run_id_fkey
  foreign key (run_id) references runs(run_id) on delete cascade;

-- 3) 인덱스
create index if not exists runs_user_created_idx on runs(user_id, created_at desc);
create index if not exists vfs_nodes_prefix_idx   on vfs_nodes(run_id, path);

-- 4) RLS — 방어선 전용(백엔드 service_role 우회). anon 키 직접 접근 차단.
alter table runs      enable row level security;
alter table vfs_nodes enable row level security;
alter table profiles  enable row level security;

drop policy if exists runs_owner on runs;
create policy runs_owner on runs
  for all using (user_id = auth.uid()::text) with check (user_id = auth.uid()::text);

drop policy if exists vfs_owner on vfs_nodes;
create policy vfs_owner on vfs_nodes
  for all using (
    exists (select 1 from runs r
            where r.run_id = vfs_nodes.run_id and r.user_id = auth.uid()::text)
  );

drop policy if exists profiles_owner on profiles;
create policy profiles_owner on profiles
  for all using (user_id = auth.uid()::text) with check (user_id = auth.uid()::text);
