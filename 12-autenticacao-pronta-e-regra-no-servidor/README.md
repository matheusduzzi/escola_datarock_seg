# Aula 13: Autenticação pronta e regra no servidor

Essa pasta tem a Loja Aurora da aula: o mesmo app do curso, agora com o Clube Aurora, o crédito de troca, o painel de pedidos da Renata e um provedor de autenticação já ligado. As falhas estão aí de propósito.

Os comandos partem dessa pasta. No Windows, troque `python3` por `py`.

```
python3 checar.py           # testa as sete falhas da aula; sai 1 enquanto alguma estiver aberta
python3 -m unittest -v      # testa o uso normal da loja; passa antes e depois da correção
python3 app.py              # abre a loja em http://127.0.0.1:8765; Ctrl+C para parar
python3 dados.py            # apaga e recria os dois bancos com os dados do começo
python3 ../loja-aurora/sondar.py --app .   # o teste comum do curso, nesse app
```

O `checar.py` e os testes sobem uma cópia da loja numa porta livre do seu computador, com bancos novos numa pasta temporária, e desligam no fim. Eles não mexem nos bancos que o `app.py` usa.

## O que tem aqui

| Arquivo | O que é | Você mexe? |
|---|---|---|
| `app.py` | o servidor da loja, como o agente do Diego escreveu | sim |
| `front/index.html` | a página da loja, com as regras do Clube e do crédito no JavaScript | não precisa |
| `provedor.py` | o provedor de autenticação: confere a senha, entrega o token e diz de quem ele é | não |
| `dados.py` | monta o banco do app (`aurora.db`) e o do provedor (`aurora-provedor.db`) | não |
| `checar.py` | manda os pedidos de um cliente curioso e diz o que continua aberto | não |
| `test_app.py` | os pedidos do cliente honesto | não |
| `relatorio-renata.md` | o modelo do resumo do exercício | copie como `meu-relatorio.md` |
| `.env.exemplo` | a configuração da loja, com chaves de teste que não abrem conta nenhuma | não |

## O provedor do kit

O `provedor.py` faz, no seu computador e sem internet, o papel de um serviço como o Supabase Auth, o Auth0, o Firebase Authentication ou o Clerk. As contas e as senhas dele são as mesmas da loja. No app de verdade, esse código é do serviço, não seu: por isso ele não entra no exercício.

## As contas de teste

| Conta | Senha | Papel | Plano | Crédito de troca |
|---|---|---|---|---|
| `bia@cliente.example` | `Bia#teste1` | cliente | Clube | R$ 0,00 |
| `caio@cliente.example` | `Caio#teste2` | cliente | grátis | R$ 0,00 |
| `duda@cliente.example` | `Duda#teste3` | cliente | grátis | R$ 15,00 |
| `renata@aurora.example` | `Renata#teste4` | admin | grátis | R$ 0,00 |

Os nomes, e-mails e pedidos são inventados. O domínio `example` não entrega mensagem para ninguém. As senhas estão aqui porque são do kit.

## A regra do curso

Todo pedido "de cliente curioso" dessa aula vai para a Loja Aurora, no seu computador. Não faça isso em site, app ou sistema de outra pessoa ou empresa. O app escuta só em `127.0.0.1` e não deve ser publicado.

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Nunca cole token, senha ou dado pessoal.
