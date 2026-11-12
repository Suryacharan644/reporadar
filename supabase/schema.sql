-- RepoRadar persistence schema for shared reports.
-- Apply in the Supabase SQL editor (or `supabase db push`).
--
-- Only the backend writes here, using the service-role key. Row-level security
-- is enabled with no policies, so the public anon key cannot read or write rows.

create table if not exists public.reports (
  id               text primary key,
  repo_full_name   text        not null,
  score            integer     not null check (score between 0 and 100),
  grade            text        not null,
  report           jsonb       not null,
  created_at       timestamptz not null default now()
);

create index if not exists reports_repo_full_name_idx on public.reports (repo_full_name);

alter table public.reports enable row level security;

-- Intentionally no policies: deny all access except the service role.
