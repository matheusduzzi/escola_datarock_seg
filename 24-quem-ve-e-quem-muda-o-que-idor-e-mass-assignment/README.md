# Aula 16: Quem vê e quem muda o quê: IDOR e mass assignment

Essa pasta tem a Loja Aurora da aula. O login já passa pelo provedor e o preço, o plano e o painel já são decididos no servidor. O que é novo são as telas que o Diego pediu ao agente: "Meus pedidos", a nota de cada pedido e "Meu perfil". As falhas delas estão aí de propósito.

Os comandos partem dessa pasta. No Windows, troque `python3` por `py`.

```
python3 checar.py           # testa as sete falhas da aula; sai 1 enquanto alguma estiver aberta
python3 -m unittest -v      # testa o uso normal da loja; passa antes e depois da correção
python3 app.py              # abre a loja em http://127.0.0.1:8765; Ctrl+C para parar
python3 dados.py            # apaga e recria os bancos e as notas com os dados do começo
python3 ../loja-aurora/sondar.py --app .   # o teste comum do curso, nesse app
```

O `checar.py` e os testes sobem uma cópia da loja numa porta livre do seu computador, com bancos e notas novos numa pasta temporária, e desligam no fim. Eles não mexem nos arquivos que o `app.py` usa.

## O que tem aqui

| Arquivo | O que é | Você mexe? |
|---|---|---|
| `app.py` | o servidor da loja, com as rotas novas que o agente do Diego escreveu | sim |
| `front/index.html` | a página da loja: perfil, meus pedidos, nota | não precisa |
| `bucket.py` | o bucket de arquivos das notas: público ou privado, endereço fixo ou link assinado | não |
| `provedor.py` | o provedor de autenticação, o mesmo da aula «Autenticação pronta e regra no servidor» | não |
| `dados.py` | monta `aurora.db`, `aurora-provedor.db` e a pasta `aurora-notas/` | não |
| `checar.py` | entra como o Caio, manda os pedidos sem a tela e diz o que continua aberto | não |
| `test_app.py` | os pedidos do cliente honesto | não |
| `relatorio-renata.md` | o modelo do resumo do exercício | copie como `meu-relatorio.md` |
| `.env.exemplo` | a configuração da loja, com chaves de teste que não abrem conta nenhuma | não |

O `test_perfil.py` do exercício é seu: você cria nessa pasta.

## O bucket do kit

O `bucket.py` faz, no seu computador e sem internet, o papel de um serviço de arquivos como o Supabase Storage ou o Amazon S3. Ele guarda as notas em `aurora-notas/` e responde no endereço `/arquivos/notas/<arquivo>`. No app de verdade, esse código é do serviço, não seu: por isso ele não entra no exercício.

## As contas de teste

| Conta | Senha | Plano | Admin | Crédito de troca | Pedidos |
|---|---|---|---|---|---|
| `bia@cliente.example` | `Bia#teste1` | Clube | não | R$ 0,00 | 1 e 2 |
| `caio@cliente.example` | `Caio#teste2` | grátis | não | R$ 0,00 | 3 |
| `duda@cliente.example` | `Duda#teste3` | grátis | não | R$ 15,00 | 4 |
| `renata@aurora.example` | `Renata#teste4` | grátis | sim | R$ 0,00 | nenhum |

A nota de cada pedido tem o mesmo número: o pedido 1 tem a `nota-0001.txt`. Na tabela `usuarios`, o crédito de troca fica na coluna `creditos`, em centavos, e o acesso de admin na coluna `is_admin`.

Os nomes, e-mails, telefones, endereços e pedidos são inventados. O domínio `example` não entrega mensagem para ninguém. As senhas estão aqui porque são do kit.

## A regra do curso

Todo pedido "de cliente curioso" dessa aula vai para a Loja Aurora, no seu computador. Não troque números de URL nem mande campos a mais em site, app ou sistema de outra pessoa ou empresa. O app escuta só em `127.0.0.1` e não deve ser publicado.

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Nunca cole token, senha ou dado pessoal.
