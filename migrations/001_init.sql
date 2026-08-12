-- ==============================================================================
-- MIGRATION 001: Init Pulse Schema (Assisted Mode)
-- ==============================================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. Sources (RSS feeds)
create table if not exists sources (
    id text primary key,
    name text not null,
    url text not null,
    category text default 'general',
    enabled boolean default true,
    created_at timestamptz default now()
);

-- 2. News Items
create table if not exists news_items (
    id uuid primary key default gen_random_uuid(),
    source_id text references sources(id),
    headline text not null,
    url text unique not null,
    published_at timestamptz,
    collected_at timestamptz default now()
);

-- 3. Users (Telegram bot readers & buyers)
create table if not exists users (
    id bigint primary key, -- Telegram user_id
    username text,
    first_name text,
    last_name text,
    is_blocked boolean default false,
    tenant_id uuid,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- 4. Words (Reader daily submitted words)
create table if not exists words (
    id uuid primary key default gen_random_uuid(),
    user_id bigint not null references users(id),
    username text,
    word text not null,
    likes int default 0,
    tenant_id uuid,
    created_at timestamptz default now()
);

-- 5. Guesses (Forward reference declaration for foreign keys)
create table if not exists guesses (
    id uuid primary key default gen_random_uuid(),
    issue_id uuid, -- foreign key constraint added below
    user_id bigint not null references users(id),
    username text,
    text text not null,
    votes int default 0,
    tenant_id uuid,
    created_at timestamptz default now()
);

-- 6. Issues (Daily poster releases)
create table if not exists issues (
    id uuid primary key default gen_random_uuid(),
    date date unique not null,
    brief_used text,
    caption text,
    image_url text,
    image_url_hires text,
    top_words jsonb default '[]'::jsonb,
    top_news jsonb default '[]'::jsonb,
    status text default 'draft', -- draft | awaiting_image | ready | published | skipped
    sponsor text,
    source_tool text default 'chatgpt',
    intake_at timestamptz,
    published_at timestamptz,
    tg_message_id bigint,
    winner_guess_id uuid references guesses(id),
    tenant_id uuid,
    created_at timestamptz default now()
);

-- Add foreign key constraint for guesses -> issues
alter table guesses
    add constraint fk_guesses_issue
    foreign key (issue_id) references issues(id) on delete cascade;

-- 7. Briefs History
create table if not exists briefs_history (
    id uuid primary key default gen_random_uuid(),
    issue_id uuid references issues(id) on delete cascade,
    brief_text text not null,
    top_words jsonb,
    top_news jsonb,
    author_notes text,
    created_at timestamptz default now()
);

-- 8. Reserve Posters (Fallback pool)
create table if not exists reserve_posters (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    image_url text not null,
    image_url_hires text,
    caption text,
    is_used boolean default false,
    used_at timestamptz,
    created_at timestamptz default now()
);

-- 9. Commercial Orders (Custom posters)
create table if not exists orders (
    id uuid primary key default gen_random_uuid(),
    user_id bigint references users(id),
    customer_tg text not null,
    tier_id text not null,
    brief_description text not null,
    amount decimal(12, 2) not null,
    status text default 'pending', -- pending | paid | in_progress | delivered | cancelled
    hires_image_url text,
    tenant_id uuid,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- 10. System Audit Events
create table if not exists events (
    id uuid primary key default gen_random_uuid(),
    event_type text not null,
    issue_id uuid references issues(id),
    order_id uuid references orders(id),
    user_id bigint,
    payload jsonb default '{}'::jsonb,
    tenant_id uuid,
    created_at timestamptz default now()
);

-- ==============================================================================
-- INDEXES & SECURITY
-- ==============================================================================
create index if not exists idx_words_user_date on words(user_id, created_at desc);
create unique index if not exists idx_news_items_url on news_items(url);
create unique index if not exists idx_issues_date on issues(date);
create index if not exists idx_guesses_issue_votes on guesses(issue_id, votes desc);
create index if not exists idx_events_type_date on events(event_type, created_at desc);

-- Enable RLS on all public tables by default
alter table sources enable row level security;
alter table news_items enable row level security;
alter table users enable row level security;
alter table words enable row level security;
alter table guesses enable row level security;
alter table issues enable row level security;
alter table briefs_history enable row level security;
alter table reserve_posters enable row level security;
alter table orders enable row level security;
alter table events enable row level security;

