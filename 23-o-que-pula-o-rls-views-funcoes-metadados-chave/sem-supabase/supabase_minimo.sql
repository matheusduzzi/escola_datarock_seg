-- O mínimo do Supabase para as regras desta aula rodarem num PostgreSQL 15 ou mais novo, sem Docker.
-- NÃO rode isso no Supabase: ele já tem tudo o que está aqui (e mais). O arquivo para sozinho se achar o schema auth.
--
-- O que ele cria, com os mesmos nomes do Supabase:
--   os papéis anon, authenticated e service_role (este com BYPASSRLS, como a chave secreta);
--   auth.uid(), auth.jwt(), auth.role() e auth.email(), que leem o token da requisição;
--   auth.users, só com as colunas que o Security Advisor consulta;
--   storage.buckets e storage.objects, só com as colunas que a aula usa.
-- Não tem API, login, painel nem arquivo de verdade no storage. A regra do banco é a mesma.

do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'auth') then
    raise exception 'Esse banco já tem o schema auth (é um Supabase?). Não rode o supabase_minimo.sql nele.';
  end if;
end $$;

create role anon nologin noinherit;
create role authenticated nologin noinherit;
create role service_role nologin noinherit bypassrls;

create schema auth;
create schema storage;
grant usage on schema public, auth, storage to anon, authenticated, service_role;

-- O PostgREST grava o token da requisição em request.jwt.claims. As funções leem dali.
create function auth.jwt() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim', true), ''),
                  nullif(current_setting('request.jwt.claims', true), ''))::jsonb
$$;
create function auth.uid() returns uuid language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'))::uuid
$$;
create function auth.role() returns text language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role'))::text
$$;
create function auth.email() returns text language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.email', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email'))::text
$$;

create table auth.users (
  id uuid primary key,
  email text,
  raw_user_meta_data jsonb,
  raw_app_meta_data jsonb
);

create table storage.buckets (
  id text primary key,
  name text not null unique,
  public boolean not null default false,
  created_at timestamptz default now()
);
create table storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets (id),
  name text not null,
  owner_id text,
  created_at timestamptz default now(),
  metadata jsonb
);
create unique index bucketid_objname on storage.objects (bucket_id, name);
alter table storage.buckets enable row level security;
alter table storage.objects enable row level security;
grant select, insert, update, delete on storage.buckets, storage.objects to anon, authenticated, service_role;

create function storage.foldername(name text) returns text[] language sql immutable as $$
  select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'), 1) - 1]
$$;
