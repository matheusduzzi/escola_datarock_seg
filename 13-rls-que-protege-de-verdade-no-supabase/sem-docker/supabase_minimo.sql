-- Só para quem roda a aula num Postgres comum, sem o Supabase.
-- NÃO rode isto num projeto Supabase: lá, tudo isto já existe.
--
-- Cria o mínimo que o Supabase traz e que a aula usa:
--   - os papéis anon (quem não entrou) e authenticated (quem entrou);
--   - a tabela auth.users, só com id e e-mail;
--   - a função auth.uid(), com a mesma definição do Supabase Auth: ela lê o id do usuário
--     que o servidor da API guarda na transação (request.jwt.claim.sub ou request.jwt.claims).
--
--   psql "$BANCO" -v ON_ERROR_STOP=1 -f sem-docker/supabase_minimo.sql

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
end
$$;

create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key,
  email text
);

create or replace function auth.uid() returns uuid
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;

grant usage on schema public to anon, authenticated;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
