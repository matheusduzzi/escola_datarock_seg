# Minha tabela dos guardrails

Copie este arquivo como `minha-tabela.md` e preencha. Use `BARRA` ou `passa` em cada coluna de guardrail, como a saída dos scripts.

## Como eu montei

- Regra fixa: arquivo de regras usado: ______ (o `regras.json` do kit ou a sua versão)
- Com modelo: n8n (nó Guardrails) ou `guardrail_modelo.py`: ______
- Modelo, provedor e limiar: ______
- A imagem da mensagem 16 foi para o modelo? ______

## As 16 mensagens

| id | entrada, regra | entrada, modelo | saída, regra | saída, modelo | pedido ou ordem plantada? | bloqueio sem motivo? | o que segura na aula 11 |
|---|---|---|---|---|---|---|---|
| 01 | | | | | | | |
| 02 | | | | | | | |
| 03 | | | | | | | |
| 04 | | | | | | | |
| 05 | | | | | | | |
| 06 | | | | | | | |
| 07 | | | | | | | |
| 08 | | | | | | | |
| 09 | | | | | | | |
| 10 | | | | | | | |
| 11 | | | | | | | |
| 12 | | | | | | | |
| 13 | | | | | | | |
| 14 | | | | | | | |
| 15 | | | | | | | |
| 16 | | | | | | | |

Na última coluna, use uma ou mais destas camadas:

- **rascunho no lugar de enviar**: o que sai para fora vira rascunho, e uma pessoa aprova;
- **consulta só de quem escreveu**: a ferramenta de pedidos só retorna os pedidos de quem mandou a mensagem;
- **ação sensível sem ferramenta**: estorno, desconto, pagamento e senha não são ferramentas do assistente;
- **segredo fora do alcance**: a chave fica no servidor, dentro da ferramenta, e o prompt não tem nada secreto;
- **busca só nos documentos da loja**: o atendimento não lê página qualquer da internet;
- **remetente autorizado**: pedido interno só vale de quem está na lista da equipe.

## O que eu medi

- Regra fixa, entrada: barrou ___ de 16. Bloqueios sem motivo: ___
- Regra fixa, saída: barrou ___ de 16. Bloqueios sem motivo: ___
- Com modelo, entrada: barrou ___ de 16. Bloqueios sem motivo: ___
- Com modelo, saída: barrou ___ de 16. Bloqueios sem motivo: ___
- Ordens plantadas que passaram pelos dois guardrails: ___

## Quanto custou a checagem com modelo

| | entrada | saída |
|---|---|---|
| chamadas ao modelo | | |
| tokens de entrada | | |
| tokens de saída | | |
| tempo total e média por texto | | |
| preço por milhão de tokens (página do provedor, com a data) | | |
| custo da rodada | | |

## Minhas regras ajustadas

- O que eu mudei no arquivo de regras: ______
- Quantas ordens plantadas a mais ele barrou: ______
- Bloqueios sem motivo novos: ______

## A mensagem 16 e a mensagem 13

- O que está escrito no print da mensagem 16, e qual guardrail leu isso: ______
- O que a resposta da mensagem 13 entrega, e para quem: ______
