-- Loja Aurora: o banco da aula «O que pula o RLS». Tem cinco portas abertas de propósito.
set client_min_messages = warning;
-- Rodar de novo apaga e recria as tabelas da aula (clientes, pedidos, papeis, cupons) com os dados do começo.
-- Rode com: python3 portas.py montar

drop view if exists public.v_clientes;
drop function if exists public.marcar_pago(bigint);
drop table if exists public.pedidos, public.clientes, public.papeis, public.cupons cascade;

create table public.clientes (
  id uuid primary key,
  nome text not null,
  email text not null,
  cidade text not null,
  telefone text not null
);

create table public.pedidos (
  id bigint primary key,
  cliente_id uuid not null references public.clientes (id),
  produto text not null,
  total_centavos integer not null,
  status text not null
);

create table public.papeis (
  user_id uuid primary key,
  papel text not null
);

create table public.cupons (
  codigo text primary key,
  desconto_pct integer not null,
  uso text not null
);

-- Em projetos do Supabase com a configuração padrão antiga, toda tabela nova do public já nasce
-- com esses acessos (a plataforma está mudando isso). A linha deixa o banco igual em qualquer caso.
grant select, insert, update, delete on public.clientes, public.pedidos, public.papeis, public.cupons
  to anon, authenticated, service_role;

insert into public.clientes values
  ('b1a00000-0000-4000-8000-000000000001', 'Bia Santos', 'bia@cliente.example', 'Campinas', '(19) 90000-0001'),
  ('ca100000-0000-4000-8000-000000000002', 'Caio Lima',  'caio@cliente.example', 'Sorocaba', '(15) 90000-0002'),
  ('d0da0000-0000-4000-8000-000000000003', 'Duda Rocha', 'duda@cliente.example', 'Santos',   '(13) 90000-0003');

insert into public.pedidos values
  (1, 'b1a00000-0000-4000-8000-000000000001', 'Luminária de mesa Aurora', 24990, 'pago'),
  (2, 'b1a00000-0000-4000-8000-000000000001', 'Vela aromática Alecrim (2)', 13980, 'aguardando pagamento'),
  (3, 'ca100000-0000-4000-8000-000000000002', 'Luminária de piso Arco', 58900, 'pago'),
  (4, 'd0da0000-0000-4000-8000-000000000003', 'Manta de algodão Serra', 15990, 'aguardando pagamento');

-- A Renata, dona da loja, é a única admin.
insert into public.papeis values ('a0000000-0000-4000-8000-0000000000aa', 'admin');

insert into public.cupons values
  ('AURORA10', 10, 'cliente'),
  ('FRETE0', 5, 'cliente'),
  ('EQUIPE40', 40, 'só funcionário');

-- A regra da aula passada, que continua certa: cada cliente lê só o que é dele.
alter table public.clientes enable row level security;
alter table public.pedidos enable row level security;
alter table public.papeis enable row level security;

create policy "cliente lê o próprio cadastro" on public.clientes
  for select to authenticated using (id = (select auth.uid()));
create policy "cliente lê os próprios pedidos" on public.pedidos
  for select to authenticated using (cliente_id = (select auth.uid()));
create policy "cada um lê o próprio papel" on public.papeis
  for select to authenticated using (user_id = (select auth.uid()));

-- Porta 1. A tela "Minha conta" lê o cadastro por esta view.
create view public.v_clientes as
  select id, nome, email, cidade from public.clientes;
grant select on public.v_clientes to anon, authenticated;

-- Porta 2. O botão "marcar como pago" do painel da Renata chama esta função.
-- Ela é security definer porque cliente não tem policy de update em pedidos.
create function public.marcar_pago(p_pedido bigint) returns text
language plpgsql security definer as $$
begin
  update pedidos set status = 'pago' where id = p_pedido;
  return 'pedido ' || p_pedido || ' marcado como pago';
end $$;

-- Porta 3. O painel da Renata lê todos os pedidos com esta policy.
create policy "admin lê todos os pedidos" on public.pedidos
  for select to authenticated
  using ((auth.jwt() -> 'user_metadata' ->> 'papel') = 'admin');

-- A tabela cupons ficou sem RLS. O Security Advisor acha.
