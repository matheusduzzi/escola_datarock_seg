# Aula 17: Webhook, limite de requisições e consulta parametrizada

Essa pasta tem a Loja Aurora da aula. É o app como ficou depois das aulas de autenticação e de IDOR: login pelo provedor, regra de preço e de plano no servidor, cada pedido visível só para o dono. Em cima disso, o agente do Diego acrescentou a busca com ordem e limite, a newsletter, o assistente de iluminação com IA e o webhook do gateway de pagamento. As falhas dessa aula estão aí de propósito.

Os comandos partem dessa pasta. No Windows, troque `python3` por `py`.

```
python3 checar.py                 # testa as nove falhas da aula; sai 1 enquanto alguma estiver aberta
python3 -m unittest test_busca    # o teste que quebrou a busca: falha até a consulta virar parametrizada
python3 -m unittest test_app      # testa o uso normal da loja; passa antes e depois da correção
python3 -m unittest               # os dois juntos: no fim da aula, OK
python3 app.py                    # abre a loja em http://127.0.0.1:8765; Ctrl+C para parar
python3 cadastro_em_massa.py      # com o app aberto, em outro terminal: 50 inscrições seguidas na newsletter
python3 gateway.py 4 pago         # com o app aberto: o gateway avisa que o pedido 4 foi pago
python3 dados.py                  # apaga e recria os dois bancos com os dados do começo
python3 ../loja-aurora/sondar.py --app .   # o teste comum do curso, nesse app
```

O `checar.py` e os testes sobem uma cópia da loja numa porta livre do seu computador, com bancos novos numa pasta temporária, e desligam no fim. Eles não mexem nos bancos que o `app.py` usa.

## O que tem aqui

| Arquivo | O que é | Você mexe? |
|---|---|---|
| `app.py` | o servidor da loja, como o agente do Diego escreveu | sim |
| `front/index.html` | a página da loja, com busca, newsletter e assistente | não precisa |
| `limitador.py` | o limite de requisições por janela de tempo, no papel de uma biblioteca pronta | não |
| `gateway.py` | o gateway de pagamento: monta e assina os eventos que vão para o webhook | não |
| `modelo.py` | o modelo de IA do assistente: responde e anota cada chamada, como o painel de uso do provedor | não |
| `provedor.py` | o provedor de autenticação | não |
| `dados.py` | monta o banco do app (`aurora.db`) e o do provedor (`aurora-provedor.db`) | não |
| `checar.py` | manda os pedidos de um robô ou de um curioso e diz o que continua aberto | não |
| `test_busca.py` | o pedido de uma cliente que busca o abajur Gota d'Água | não |
| `test_app.py` | os pedidos do cliente honesto, do gateway e do assistente | não |
| `cadastro_em_massa.py` | o robô da newsletter, só contra a loja no seu computador | não |
| `relatorio-renata.md` | o modelo do inventário e do resumo do exercício | copie como `meu-relatorio.md` |
| `.env.exemplo` | a configuração da loja, com o segredo do webhook de teste | não |

## O gateway e o modelo do kit

O `gateway.py` faz o papel do gateway de pagamento de verdade. Cada evento tem um `evento_id` e vai assinado com o `WEBHOOK_SEGREDO` do `.env.exemplo`: um HMAC-SHA256 do corpo exato, no cabeçalho `X-Aurora-Assinatura`. Quando a loja não responde 2xx, ele manda o mesmo evento de novo.

O `modelo.py` faz o papel de uma API paga de modelo de IA, sem internet e sem custo. Cada chamada fica anotada na tabela `chamadas_modelo`. No app de verdade, cada uma dessas linhas é uma cobrança na conta da loja.

## As contas de teste

| Conta | Senha | Papel | Plano |
|---|---|---|---|
| `bia@cliente.example` | `Bia#teste1` | cliente | Clube |
| `caio@cliente.example` | `Caio#teste2` | cliente | grátis |
| `duda@cliente.example` | `Duda#teste3` | cliente | grátis |
| `renata@aurora.example` | `Renata#teste4` | admin | grátis |

O pedido 4 é da Duda e começa como "aguardando pagamento". Os nomes, e-mails e pedidos são inventados. O domínio `example` não entrega mensagem para ninguém.

## A regra do curso

Todo pedido de robô ou de curioso dessa aula vai para a Loja Aurora, no seu computador. O `cadastro_em_massa.py` e o `checar.py` só falam com `127.0.0.1`. Não aponte nenhum deles para site, app ou sistema de outra pessoa ou empresa, nem "só para ver". O app não deve ser publicado.

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Nunca cole token, segredo ou dado pessoal.
