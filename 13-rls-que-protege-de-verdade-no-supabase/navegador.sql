-- O pedido que a tela "Meus pedidos" manda quando o Caio entra, e o mesmo pedido sem o filtro.
--
-- No navegador, a tela chama:
--   GET /rest/v1/pedidos?select=id,produto,total_centavos,cidade&cliente_id=eq.<id do Caio>
--   com o token do Caio no cabeçalho Authorization.
-- O servidor da API do Supabase (o PostgREST) troca para o papel do token (authenticated),
-- guarda o id do Caio na transação e roda a consulta com o filtro como where.
-- Este arquivo faz o mesmo, direto no banco.
--
--   psql "$BANCO" -f navegador.sql

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', true) as "token do Caio";

-- 1. Com o filtro que a tela manda (cliente_id=eq.<id do Caio>)
select id, produto, total_centavos, cidade
from public.pedidos
where cliente_id = '22222222-2222-2222-2222-222222222222'
order by id;

-- 2. O mesmo pedido, sem o filtro
select id, produto, total_centavos, cidade
from public.pedidos
order by id;

rollback;
