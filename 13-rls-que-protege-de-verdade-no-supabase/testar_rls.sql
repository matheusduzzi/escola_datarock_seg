-- Testa a tabela de pedidos como quem usa o app: sem login, como a Bia e como o Caio,
-- nos quatro verbos (select, insert, update, delete). Nunca como administrador do banco.
--
--   psql "$BANCO" -v ON_ERROR_STOP=1 -f testar_rls.sql
--
-- Cada linha da lista abaixo é uma tentativa. Ela roda com o papel e o usuário daquela linha
-- e é desfeita logo depois: nenhum pedido muda de verdade. O resultado diz:
--   ok       a tentativa fez o que devia (barrada, ou o uso normal funcionou)
--   VAZOU    alguém leu, criou, mudou ou apagou o que não é dele
--   QUEBROU  o uso normal da loja parou de funcionar
-- O psql sai com erro (código 3) enquanto houver VAZOU ou QUEBROU, e com 0 quando tudo passa.

begin;

create temp table checagens (
  n int primary key,
  tipo text not null,          -- 'barrar' (tem que dar 0) ou 'uso normal' (tem que dar o esperado)
  quem text not null,
  verbo text not null,
  teste text not null,
  papel text,                  -- anon ou authenticated; vazio = conferência de permissão da tabela
  usuario uuid,                -- id do usuário logado; vazio = sem login
  tentativa text not null,     -- o que a pessoa tenta fazer, com o papel e o usuário da linha
  efeito text,                 -- o que mudou na tabela depois da tentativa (lido antes de desfazer)
  esperado int not null
);

-- Bia: 11111111-...   Caio: 22222222-...   Duda: 33333333-...
-- Pedidos 1 e 2 são da Bia, o 3 é do Caio, o 4 é da Duda.
insert into checagens values
  (1, 'barrar', 'sem login', 'permissão', 'o papel anon não tem permissão nenhuma na tabela',
   null, null,
   $t$select (has_table_privilege('anon', 'public.pedidos', 'select')
          or has_table_privilege('anon', 'public.pedidos', 'insert')
          or has_table_privilege('anon', 'public.pedidos', 'update')
          or has_table_privilege('anon', 'public.pedidos', 'delete'))::int$t$,
   null, 0),
  (2, 'barrar', 'sem login', 'select', 'lê os pedidos da loja',
   'anon', null,
   $t$select count(*) from public.pedidos$t$,
   null, 0),
  (3, 'barrar', 'sem login', 'insert', 'cria um pedido em nome da Bia',
   'anon', null,
   $t$insert into public.pedidos (cliente_id, produto, quantidade, total_centavos, observacao)
       values ('11111111-1111-1111-1111-111111111111', 'Fita de LED quente 5 m', 9, 100, 'criado sem login')$t$,
   $t$select count(*) from public.pedidos where observacao = 'criado sem login'$t$, 0),
  (4, 'barrar', 'sem login', 'update', 'cancela o pedido 1 da Bia',
   'anon', null,
   $t$update public.pedidos set status = 'cancelado' where id = 1$t$,
   $t$select count(*) from public.pedidos where id = 1 and status = 'cancelado'$t$, 0),
  (5, 'barrar', 'sem login', 'delete', 'apaga o pedido 1 da Bia',
   'anon', null,
   $t$delete from public.pedidos where id = 1$t$,
   $t$select 1 - count(*) from public.pedidos where id = 1$t$, 0),
  (6, 'barrar', 'Caio', 'select', 'tira o filtro e lê pedidos de outros clientes',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$select count(*) from public.pedidos where cliente_id <> '22222222-2222-2222-2222-222222222222'$t$,
   null, 0),
  (7, 'barrar', 'Bia', 'select', 'tira o filtro e lê pedidos de outros clientes',
   'authenticated', '11111111-1111-1111-1111-111111111111',
   $t$select count(*) from public.pedidos where cliente_id <> '11111111-1111-1111-1111-111111111111'$t$,
   null, 0),
  (8, 'barrar', 'Caio', 'insert', 'cria um pedido em nome da Bia',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$insert into public.pedidos (cliente_id, produto, quantidade, total_centavos, observacao)
       values ('11111111-1111-1111-1111-111111111111', 'Fita de LED quente 5 m', 9, 100, 'criado pelo Caio')$t$,
   $t$select count(*) from public.pedidos where observacao = 'criado pelo Caio'$t$, 0),
  (9, 'barrar', 'Caio', 'update', 'cancela o pedido 1 da Bia',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$update public.pedidos set status = 'cancelado' where id = 1$t$,
   $t$select count(*) from public.pedidos where id = 1 and status = 'cancelado'$t$, 0),
  -- Sem where, o banco não passa a linha nova pela policy de select: quem segura é o with check.
  (10, 'barrar', 'Caio', 'update', 'passa os pedidos dele para a Bia, sem where',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$update public.pedidos set cliente_id = '11111111-1111-1111-1111-111111111111'$t$,
   $t$select count(*) from public.pedidos where id in (3, 4) and cliente_id = '11111111-1111-1111-1111-111111111111'$t$, 0),
  (11, 'barrar', 'Caio', 'delete', 'apaga o pedido 1 da Bia',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$delete from public.pedidos where id = 1$t$,
   $t$select 1 - count(*) from public.pedidos where id = 1$t$, 0),
  (12, 'uso normal', 'Bia', 'select', 'lê os 2 pedidos dela',
   'authenticated', '11111111-1111-1111-1111-111111111111',
   $t$select count(*) from public.pedidos where cliente_id = '11111111-1111-1111-1111-111111111111'$t$,
   null, 2),
  (13, 'uso normal', 'Caio', 'select', 'lê o pedido dele',
   'authenticated', '22222222-2222-2222-2222-222222222222',
   $t$select count(*) from public.pedidos where cliente_id = '22222222-2222-2222-2222-222222222222'$t$,
   null, 1),
  (14, 'uso normal', 'Bia', 'insert', 'cria um pedido dela',
   'authenticated', '11111111-1111-1111-1111-111111111111',
   $t$insert into public.pedidos (cliente_id, produto, quantidade, total_centavos, observacao)
       values ('11111111-1111-1111-1111-111111111111', 'Almofada linho Cru', 1, 7990, 'pedido novo da Bia')$t$,
   $t$select count(*) from public.pedidos where observacao = 'pedido novo da Bia'
        and cliente_id = '11111111-1111-1111-1111-111111111111'$t$, 1),
  (15, 'uso normal', 'Bia', 'update', 'escreve uma observação no pedido 1, dela',
   'authenticated', '11111111-1111-1111-1111-111111111111',
   $t$update public.pedidos set observacao = 'entregar à tarde' where id = 1$t$,
   $t$select count(*) from public.pedidos where id = 1 and observacao = 'entregar à tarde'$t$, 1),
  (16, 'uso normal', 'Bia', 'delete', 'cancela o pedido 2, dela, que não foi pago',
   'authenticated', '11111111-1111-1111-1111-111111111111',
   $t$delete from public.pedidos where id = 2$t$,
   $t$select 1 - count(*) from public.pedidos where id = 2$t$, 1);

create table pg_temp.resultados (n int, resultado text, quem text, verbo text, teste text, aconteceu text);

do $$
declare
  c record;
  n bigint;
  efeito bigint;
  erro text;
  valor bigint;
  aconteceu text;
begin
  for c in select * from checagens order by n loop
    n := null; efeito := null; erro := null;
    begin
      if c.papel is not null then
        execute format('set local role %I', c.papel);
        perform set_config('request.jwt.claim.sub', coalesce(c.usuario::text, ''), true);
      end if;
      begin
        if c.verbo in ('select', 'permissão') then
          execute c.tentativa into n;
        else
          execute c.tentativa;  -- sem returning, como a API pode mandar
          get diagnostics n = row_count;
        end if;
      exception when others then
        erro := sqlstate || ' ' || sqlerrm;
      end;
      reset role;
      if c.efeito is not null then
        execute c.efeito into efeito;
      end if;
      raise exception using errcode = 'P0099', message = 'desfazer a tentativa';
    exception when sqlstate 'P0099' then
      null;  -- a tentativa foi desfeita; n, efeito e erro ficam guardados
    end;

    valor := coalesce(efeito, case when erro is null then n else 0 end);
    if c.verbo = 'permissão' then
      aconteceu := case when valor = 0 then 'sem permissão' else 'tem permissão' end;
    elsif erro is not null and valor = 0 then
      aconteceu := 'recusado (' || split_part(erro, ' ', 1) || ')';
    else
      aconteceu := case c.verbo
        when 'select' then 'viu ' || valor
        when 'insert' then 'criou ' || valor
        when 'update' then 'mudou ' || valor
        when 'delete' then 'apagou ' || valor
      end || case when valor = 1 then ' pedido' else ' pedidos' end;
    end if;

    insert into pg_temp.resultados values (
      c.n,
      case when valor = c.esperado then 'ok'
           when c.tipo = 'barrar' then 'VAZOU'
           else 'QUEBROU' end,
      c.quem, c.verbo, c.teste, aconteceu);
  end loop;
end
$$;

select resultado, quem, verbo, teste, aconteceu
from pg_temp.resultados
order by n;

select count(*) filter (where resultado = 'ok') || ' de ' || count(*) || ' ok.' as resumo
from pg_temp.resultados;

do $$
declare
  falhas int;
begin
  select count(*) into falhas from pg_temp.resultados where resultado <> 'ok';
  if falhas > 0 then
    raise exception '% de 16 checagens falharam. Nada foi gravado.', falhas;
  end if;
end
$$;

rollback;
