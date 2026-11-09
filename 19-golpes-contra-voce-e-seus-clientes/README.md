# 23. Golpes contra você e seus clientes

Os comandos da aula partem desta pasta. Você precisa do Python (3.9 ou mais novo). No Windows, troque `python3` por `py`.

O kit não abre link nenhum, não chama modelo de IA e não fala com gateway nenhum. Ele lê arquivos de texto.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `checkout-sexta.csv` | as 114 tentativas de pagamento da sexta da Black Friday, como o painel do gateway exporta |
| `checkout-sabado.csv` | as tentativas de sábado, para o exercício |
| `resumir_checkout.py` | agrupa as tentativas por uma coluna e conta tentativas, cartões, recusas e aprovadas |
| `links.txt` | os links que chegaram à equipe e aos clientes na semana |
| `dono_do_link.py` | diz qual é o site de verdade de cada link e se ele é da loja, sem abrir |
| `pedidos-urgentes.md` | os seis pedidos urgentes do fim de semana, para o exercício |
| `fatos-da-loja.md` | como a Loja Aurora fala com os clientes, paga e devolve dinheiro, para o aviso |
| `minhas-respostas.md` | onde você responde o exercício |

## Rodar

```
python3 resumir_checkout.py checkout-sexta.csv
python3 resumir_checkout.py checkout-sexta.csv --onde sessao=s-gtx7 --linhas
python3 dono_do_link.py links.txt
```

O `resumir_checkout.py` aceita:

| Opção | O que faz |
|---|---|
| `--por COLUNA` | agrupa por essa coluna; sem ela, agrupa por `sessao` |
| `--onde COLUNA=VALOR` | usa só as linhas com esse valor; pode repetir |
| `--linhas` | mostra as linhas, em vez do resumo |
| `--todos` | mostra todos os grupos, não só os 8 com mais tentativas |

Ele sai com 0 quando lê o arquivo e com 2 quando não consegue. Isso acontece com caminho errado, arquivo vazio, coluna que falta, valor ou resultado que não dá para ler. Ele não diz se é ataque: quem diz é você.

O `dono_do_link.py` sai com 0 quando todos os links são da loja. Sai com 1 quando algum não é ou não dá para ler, e com 2 quando não consegue ler o arquivo. Para testar com o domínio da sua empresa: `python3 dono_do_link.py links.txt --dominio suaempresa.com.br`. Ser da loja diz de quem é o site, não diz que a mensagem é verdadeira.

## O checkout

Uma tentativa por linha, separada por ponto e vírgula, com o valor em reais e vírgula (`24,90`):

| Coluna | O que vai |
|---|---|
| `hora` | quando a tentativa aconteceu |
| `sessao` | a sessão do navegador no checkout |
| `ip` | o endereço de onde veio |
| `email` | o e-mail digitado no checkout |
| `produto` e `valor` | o que foi comprado e o total |
| `cartao` | a impressão do cartão que o gateway calcula: o mesmo cartão tem sempre a mesma, e ela não revela o número |
| `resultado` | `aprovado` ou `recusado` |
| `motivo` | o motivo da recusa, como `generic_decline` ou `incorrect_cvc`; vazio quando aprovado |

Os IPs, e-mails e domínios dos arquivos são de faixas reservadas para exemplo: não levam a ninguém.

## As suas respostas

```
cp minhas-respostas.md minhas-respostas-preenchidas.md      # macOS e Linux
copy minhas-respostas.md minhas-respostas-preenchidas.md    # Windows
```

O `.gitignore` deixa a cópia preenchida fora do git.

Se travar, deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole código de verificação, senha ou número de cartão no comentário.
