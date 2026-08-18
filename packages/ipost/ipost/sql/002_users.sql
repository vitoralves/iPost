create table if not exists users (
  username text primary key,
  password_hash text not null,
  created_at timestamptz not null default now()
);

alter table users enable row level security;

grant all on table users to service_role;
