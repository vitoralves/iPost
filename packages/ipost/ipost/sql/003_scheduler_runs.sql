create table if not exists scheduler_runs (
  id text primary key,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists scheduler_runs_created_at on scheduler_runs (created_at desc);

alter table scheduler_runs enable row level security;

grant all on table scheduler_runs to service_role;
