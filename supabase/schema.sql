-- BridgeLedger database setup for Supabase.
-- Run once: Supabase dashboard -> SQL Editor -> New query -> paste this -> Run.
--
-- One row per person holds their whole plan. Row-level security means a
-- signed-in person can only read and change their own row; visitors who are
-- not signed in can't read anything.

create table if not exists public.plans (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  state      jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.plans enable row level security;

drop policy if exists "Read own plan"   on public.plans;
drop policy if exists "Insert own plan" on public.plans;
drop policy if exists "Update own plan" on public.plans;
drop policy if exists "Delete own plan" on public.plans;

create policy "Read own plan" on public.plans
  for select to authenticated using ((select auth.uid()) = user_id);

create policy "Insert own plan" on public.plans
  for insert to authenticated with check ((select auth.uid()) = user_id);

create policy "Update own plan" on public.plans
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Delete own plan" on public.plans
  for delete to authenticated using ((select auth.uid()) = user_id);

revoke all on public.plans from anon;
grant select, insert, update, delete on public.plans to authenticated;
