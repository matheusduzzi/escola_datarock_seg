-- A sua correção da tabela de pedidos da Loja Aurora.
--
-- Rode sempre nesta ordem. O loja.sql recria a tabela como o agente deixou, então cada
-- rodada começa do mesmo lugar:
--
--   psql "$BANCO" -v ON_ERROR_STOP=1 -f loja.sql
--   psql "$BANCO" -v ON_ERROR_STOP=1 -f correcao.sql
--   psql "$BANCO" -v ON_ERROR_STOP=1 -f testar_rls.sql
--
-- O que a Renata pediu:
--   1. Quem não entrou na loja não lê, não cria, não muda e não apaga pedido nenhum.
--   2. Cada cliente lê, cria, muda e cancela só os pedidos dele.
--   3. Ninguém cria um pedido no nome de outra pessoa nem passa um pedido seu para outra pessoa.
--
-- Escreva entre o begin e o commit.

begin;



commit;
