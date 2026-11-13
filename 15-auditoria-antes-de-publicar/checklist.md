# Checklist antes de publicar

Rode na ordem, com o PR na tela. Para cada item, anote no relatório o que você fez, o que apareceu e se virou achado. Um item que você não conseguiu fazer também vai para o relatório, com o motivo.

## 1. Testes à mão, com a loja aberta

Abra a loja da branch num terminal (`cd repo-aurora` e `python3 app.py`) e use outro terminal na pasta da aula.

1. **O plano grátis abre o que é pago?** `python3 pedir.py caio /api/clube/guia`. O Caio é do plano grátis: o certo é 403.
2. **Um cliente abre o que é do admin?** Para cada rota que começa com `/api/admin/`, rode com o `caio`. O certo é 403. Procure as rotas no `app.py` (`url.path`), inclusive as que o PR criou.
3. **Quem não entrou abre alguma coisa que não devia?** As mesmas rotas com `ninguem`. O certo é 401.
4. **O que chega ao navegador?** Abra `http://127.0.0.1:8765` no navegador, entre com a Bia e abra as ferramentas do desenvolvedor (F12), aba Rede (Network), filtro Fetch/XHR. Clique em cada pedido e leia a resposta. Nada de chave que comece com `aurora_sk_` ou `aurora_whsec_`, nada de pedido, e-mail ou crédito de outra pessoa.

## 2. Lendo o PR

5. **O que vem do cliente vai direto para o banco?** Siga até o banco cada valor que o PR lê do pedido: corpo, endereço, cabeçalho. Ele entra por `?` na consulta? Passou antes por uma lista do que é aceito (formato, tamanho, opções)?
6. **Cada rota nova está na lista de rotas, com quem chama e o que ela exige?** Rota que ninguém chama sai do app.
7. **Cada regra do PR bate com `regras-da-loja.md`?** Dia, hora, fuso, quem pode, quanto, o que soma com o quê.
8. **O PR traz dependência nova?** Ela é usada? Quem mantém? A versão está travada? (É a pergunta da aula «Dependências: o que o agente instala».)
9. **Os testes do PR testam a borda?** Meia-noite, virada do dia, cliente do Clube, quem não pode. Um teste que só usa o caso do meio passa com o bug.

## 3. As ferramentas

10. **O portão:** `python3 portao.py repo-aurora`. Ele procura chave em cada commit do PR, confere as dependências, roda as regras de código e os testes.
11. **O revisor por escopo:** uma rodada por escopo de `revisor/escopos.md`, com um agente de IA (subagente só de leitura) ou com uma pessoa. O que ele aponta é hipótese até você mostrar com um pedido ou um teste.

## 4. Para cada achado, uma decisão

- **Corrigir agora**, com o teste ou o pedido que mostrava a falha e passa a mostrar a falha fechada.
- **Falso positivo**, com o trecho da documentação que mostra por que não é falha. "Achei que não era" não serve.
- **Aceite de risco**, quando a correção não cabe antes de publicar: o que pode acontecer, o dono (quem responde pelo negócio), o prazo, o que segura o risco enquanto isso e quando o item volta.
