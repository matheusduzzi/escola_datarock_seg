# Aula 15: O que pula o RLS

O banco da Loja Aurora com cinco portas abertas de propósito, e um teste que diz quais continuam abertas. Tudo roda no seu computador.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `loja.sql` | clientes, pedidos, papéis e cupons da loja, com a view, a função e a policy da aula |
| `notas.sql` | o bucket `notas`, com as quatro notas fiscais e a policy que deixa listar |
| `front/config.js` | a configuração que o front manda para o navegador |
| `portas.py` | monta o banco, roda o seu SQL e testa as portas |
| `minha-correcao.sql` | onde você escreve a sua correção, porta por porta |
| `relatorio-advisor.md` | o modelo do relatório do Security Advisor |
| `sem-supabase/supabase_minimo.sql` | só para quem não tem Docker (veja no fim) |

O `portas.py` usa só o que vem com o Python 3.9 ou mais novo, e chama o `psql` para falar com o banco.

## Subir o Supabase no seu computador

Você precisa do Docker rodando e da CLI do Supabase. A instalação da CLI muda com o sistema: siga a página oficial, em https://supabase.com/docs/guides/local-development/cli/getting-started.

Dentro desta pasta:

```
supabase init
supabase start
```

O `supabase start` mostra os endereços do projeto. Procure o quadro Database, na linha URL. O padrão é `postgresql://postgres:postgres@127.0.0.1:54322/postgres`, que é o que o `portas.py` usa. Se a sua for outra, passe na variável `AURORA_PSQL`:

```
AURORA_PSQL="psql postgresql://postgres:postgres@127.0.0.1:54322/postgres" python3 portas.py sondar
```

Sem `psql` no computador, use o que vem dentro do contêiner do banco:

```
docker ps --format '{{.Names}}' | grep supabase_db
AURORA_PSQL="docker exec -i NOME_QUE_APARECEU psql -U postgres" python3 portas.py sondar
```

Se o Supabase da aula 14 estiver rodando, pare antes com `supabase stop` na pasta dela. Com as portas padrão, roda um projeto local por vez.

## Os comandos

```
python3 portas.py montar                      # cria o banco da aula; rodar de novo volta ao começo
python3 portas.py sondar                      # diz quais portas estão abertas
python3 portas.py aplicar minha-correcao.sql  # roda o seu SQL
python3 portas.py advisor splinter.sql        # roda as regras do Security Advisor
```

O `sondar` entra no banco como a Bia, o Caio, a Renata, um visitante sem login e a chave secreta. Cada teste roda dentro de uma transação desfeita no fim: ele não muda nenhum dado. Sai com `1` enquanto alguma porta estiver aberta ou alguma função da loja tiver quebrado, e com `0` quando tudo fecha e a loja continua funcionando. No começo, as seis portas aparecem como `ABERTA`.

O `montar` apaga e recria as tabelas da aula (`clientes`, `pedidos`, `papeis`, `cupons`). Não rode num projeto com dados seus.

## O Security Advisor

Use o primeiro que você tiver:

1. No painel do Supabase, em Advisors, a página Security Advisor.
2. No terminal, `supabase db advisors`. As opções mudam entre versões; rode `supabase db advisors --help` antes.
3. As regras do Advisor são abertas, no projeto splinter. Baixe o arquivo e rode pelo `portas.py`:

```
curl -L -o splinter.sql https://raw.githubusercontent.com/supabase/splinter/main/splinter.sql
python3 portas.py advisor splinter.sql
```

O `portas.py advisor` roda o arquivo dentro de uma transação desfeita no fim e mostra só os alertas de segurança.

## Sem Docker

Quem não consegue rodar o Docker pode usar um PostgreSQL 15 ou mais novo instalado no computador. O `sem-supabase/supabase_minimo.sql` cria o mínimo do Supabase que a aula usa: os papéis `anon`, `authenticated` e `service_role`, as funções `auth.uid()` e `auth.jwt()`, e as tabelas do storage. Ele não tem API, login nem painel, e para sozinho se você rodar num Supabase.

```
createdb aula15
psql -d aula15 -f sem-supabase/supabase_minimo.sql
AURORA_PSQL="psql -d aula15" python3 portas.py montar
AURORA_PSQL="psql -d aula15" python3 portas.py sondar
```

## A regra do curso

Os nomes, e-mails e telefones são inventados. As chaves de `front/config.js` têm o formato das chaves do Supabase e não abrem conta nenhuma. Faça os testes só nesse banco, no seu computador. Não teste nada disso no projeto de outra pessoa, nem "só para ver".

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole uma chave, senha ou dado pessoal no comentário.
