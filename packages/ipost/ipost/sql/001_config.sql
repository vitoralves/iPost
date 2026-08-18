create table if not exists topics (
  slug text primary key,
  name text not null,
  weight int not null default 10,
  enabled boolean not null default true,
  last_used text,
  created_at timestamptz not null default now()
);

create table if not exists tracks (
  id text primary key,
  title text not null,
  artist text not null default '',
  duration text not null default '',
  last_used text,
  storage_path text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists track_topics (
  track_id text not null references tracks (id) on delete cascade,
  topic_slug text not null references topics (slug) on delete cascade,
  primary key (track_id, topic_slug)
);

create table if not exists brand_kit (
  id text primary key default 'default',
  voice_tone text not null,
  banned text[] not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists style_refs (
  id text primary key,
  url text not null,
  note text not null default '',
  topic_slug text references topics (slug) on delete cascade,
  sort_order int not null default 0
);

create table if not exists jobs (
  id text primary key,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

alter table topics enable row level security;
alter table tracks enable row level security;
alter table track_topics enable row level security;
alter table brand_kit enable row level security;
alter table style_refs enable row level security;
alter table jobs enable row level security;

grant all on table topics, tracks, track_topics, brand_kit, style_refs, jobs to service_role;
