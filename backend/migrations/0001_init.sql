-- JB Marker VFS 스키마 (marker_api.md §1). provision은 Supabase creds 확보 후.
create table if not exists runs (
  run_id text primary key,
  user_id text not null default 'demo',
  title text,
  current_step text,
  step_status jsonb not null default '{}',
  languages text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists vfs_nodes (
  run_id text not null references runs(run_id),
  path text not null,
  kind text,
  mime text,
  source text,
  content_text text,
  blob_path text,
  meta jsonb not null default '{}',
  grounds jsonb,
  hash text,
  created_at timestamptz not null default now(),
  primary key (run_id, path)
);

create index if not exists vfs_nodes_prefix_idx on vfs_nodes (run_id, path);
