-- Run once in Supabase Dashboard > SQL Editor.
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists conversations_user_created_idx
  on public.conversations(user_id, created_at desc);
create index if not exists messages_conversation_created_idx
  on public.messages(conversation_id, created_at);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert on public.messages to authenticated;

create policy "Users manage their own conversations"
  on public.conversations for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users read their own messages"
  on public.messages for select to authenticated
  using (auth.uid() = user_id);

create policy "Users add messages to their own conversations"
  on public.messages for insert to authenticated
  with check (
    auth.uid() = user_id
    and exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  );
