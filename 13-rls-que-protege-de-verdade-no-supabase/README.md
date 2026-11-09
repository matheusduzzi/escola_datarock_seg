# Aula 14. RLS que protege de verdade no Supabase

A tabela de pedidos da Loja Aurora, como o agente deixou: o RLS ligado e uma policy `using (true)` em todos os verbos. Os comandos partem desta pasta.

| Arquivo | O que faz |
|---|---|
| `loja.sql` | apaga e recria a tabela `pedidos` com 4 pedidos, as permissões e a policy do agente; cria as contas de teste da Bia, do Caio e da Duda em `auth.users` |
| `navegador.sql` | faz, como o Caio, o pedido da tela "Meus pedidos" com o filtro e sem o filtro |
| `testar_rls.sql` | 16 tentativas sem login, como a Bia e como o Caio, nos quatro verbos; desfaz tudo no fim |
| `correcao.sql` | onde você escreve a correção |
| `relatorio-renata.md` | modelo do resumo para a Renata |
| `sem-docker/supabase_minimo.sql` | só para quem roda num Postgres comum: cria o mínimo que o Supabase traz |

## O que você precisa

- O **psql**, o cliente de linha de comando do Postgres. Ele vem com qualquer instalação do Postgres e também pode ser instalado sozinho.
- Um banco para rodar. Escolha um dos dois caminhos.

### Caminho 1: o Supabase no seu computador (Docker)

1. Instale o Docker e a CLI do Supabase pelo guia oficial: <https://supabase.com/docs/guides/local-development/cli/getting-started>.
2. Numa pasta nova, só para o curso, rode `supabase init` e depois `supabase start`. Na primeira vez ele baixa as imagens e demora.
3. O `supabase start` mostra a URL do banco. No padrão, ela é `postgresql://postgres:postgres@127.0.0.1:54322/postgres`. Guarde numa variável:

```
export BANCO="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
```

4. Volte para esta pasta e siga em "Rodar". Quando terminar, `supabase stop` desliga tudo.

Esse projeto local é só seu e roda só no seu computador. Não rode os arquivos da aula num projeto Supabase com clientes de verdade.

### Caminho 2: um Postgres comum, sem Docker

Com um Postgres instalado no seu computador (o kit foi testado no Postgres 16), crie um banco vazio só para a aula e rode uma vez o arquivo que imita o Supabase:

```
createdb aurora_rls
export BANCO="postgresql:///aurora_rls"
psql "$BANCO" -v ON_ERROR_STOP=1 -f sem-docker/supabase_minimo.sql
```

Ele cria os papéis `anon` e `authenticated`, a tabela `auth.users` e a função `auth.uid()` com a mesma definição do Supabase. As policies e o teste da aula são os mesmos nos dois caminhos.

No Windows, use `set BANCO=...` no lugar de `export` e `%BANCO%` no lugar de `"$BANCO"`.

## Rodar

```
psql "$BANCO" -v ON_ERROR_STOP=1 -f loja.sql
psql "$BANCO" -f navegador.sql
psql "$BANCO" -v ON_ERROR_STOP=1 -f testar_rls.sql
```

O `testar_rls.sql` termina com `5 de 16 ok.` e um erro: é assim mesmo no começo. Ele sai com código 3 enquanto alguma tentativa aparecer como `VAZOU` ou `QUEBROU`, e com 0 quando as 16 passam.

Para testar a sua correção, rode sempre do começo:

```
psql "$BANCO" -v ON_ERROR_STOP=1 -f loja.sql
psql "$BANCO" -v ON_ERROR_STOP=1 -f correcao.sql
psql "$BANCO" -v ON_ERROR_STOP=1 -f testar_rls.sql
```

## As contas de teste

| Cliente | id em `auth.users` | Pedidos |
|---|---|---|
| Bia | `11111111-1111-1111-1111-111111111111` | 1 e 2 |
| Caio | `22222222-2222-2222-2222-222222222222` | 3 |
| Duda | `33333333-3333-3333-3333-333333333333` | 4 |

Os nomes, e-mails, cidades e pedidos são inventados. As contas não têm senha: o teste entra como cada uma direto no banco, do mesmo jeito que a documentação do Supabase ensina a testar policies.

## Por que o teste não roda como `postgres`

O `postgres` é o administrador do banco e passa por cima do RLS. Se você abrir a tabela como ele, vê os 4 pedidos com ou sem policy. Por isso cada tentativa do `testar_rls.sql` troca para o papel `anon` (sem login) ou `authenticated` (logado) e diz qual usuário é, antes de tentar.

Para pedir ajuda, deixe um comentário na aula com o seu objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole chave, senha, token ou dado pessoal no comentário.
