# 07. O contrato de acesso do agente

Os arquivos da aula «O contrato de acesso do agente». Rode tudo dentro dessa pasta, com o Python 3.9 ou mais novo. Não precisa instalar nada.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `porteiro.py` | fica entre o agente e as ferramentas e aplica o contrato: faz, segura para uma pessoa confirmar ou recusa |
| `ferramentas.csv` | as ferramentas de dois agentes da Loja Aurora: o assistente de atendimento e o agente de código do Diego |
| `exemplos/rascunho-diego.csv` | o primeiro contrato que o Diego escreveu para o assistente |
| `exemplos/contrato-assistente.csv` | o contrato do assistente que a Renata aprovou |
| `pedidos/manha.jsonl` | as ferramentas que um assistente sem defesa pediria depois de ler as 15 mensagens da manhã |
| `pedidos/codigo.jsonl` | as ferramentas que o agente de código pede na tarefa do desconto, do exercício |
| `contrato-modelo.csv` | um contrato vazio, só com o cabeçalho, para você copiar |
| `meu-contrato.md` | o modelo do contrato do seu agente, nas três colunas, e o lugar das respostas do exercício |

## Os comandos

```
python3 porteiro.py checar exemplos/contrato-assistente.csv
python3 porteiro.py rodar exemplos/contrato-assistente.csv pedidos/manha.jsonl
python3 porteiro.py confirmar 2 "CANCELAR pedido 2"
python3 porteiro.py ver
python3 porteiro.py zerar
```

- `checar` lê o contrato e lista os problemas. Sai com `1` quando acha algum e com `0` quando não acha.
- `rodar` passa cada pedido do agente pelo contrato. O que está em «faz sozinho» roda. O que está em «pede confirmação» fica numa fila. O resto é recusado, inclusive o que não está no contrato. Com contrato com problema, ele nem começa.
- `confirmar` é o comando da pessoa. Recebe o número da fila e a frase que o porteiro mostrou. Frase diferente não faz nada e sai com `1`.
- `ver` mostra o banco da loja: pedidos, estornos, pagamentos e mensagens enviadas. É assim que você vê que uma ação recusada não aconteceu.
- `zerar` volta o banco, a fila e o registro ao começo. Rode antes de trocar de agente.

No Windows, troque `python3` por `py`.

O porteiro grava três arquivos na pasta: `loja.db`, `pendentes.json` e `registro.csv`, com cada decisão. O `.gitignore` deixa os três de fora do git, junto com os arquivos que você cria no exercício.

## O formato do contrato

Uma linha por ferramenta, com quatro campos:

```
ferramenta,tipo,coluna,confirmacao
cancelar_item,destrutiva,confirma,digitada
```

- `tipo`: o que a ferramenta faz de pior. Os valores estão no começo do `porteiro.py`. Para as ferramentas do kit, o tipo é o do `ferramentas.csv`, e o porteiro recusa um tipo diferente.
- `coluna`: `sozinho`, `confirma` ou `nunca`.
- `confirmacao`: só na coluna `confirma`. `sim` para um clique, `digitada` para a pessoa escrever a frase que o porteiro mostra.

Ferramenta sua, que não está no `ferramentas.csv`, também entra. O porteiro acredita no tipo que você escrever.

## O que é de verdade e o que não é

O banco da loja é um SQLite com os mesmos pedidos da Loja Aurora. As ferramentas do assistente gravam nele: um estorno vira uma linha em `estornos`, uma mensagem vira uma linha em `enviados`. As do agente de código não mexem em projeto nenhum: o porteiro só anota no registro o que teria rodado. Os nomes de pacote, endereços e e-mails dos pedidos são inventados.

Os arquivos de `pedidos/` foram escritos à mão. Nenhum modelo de IA roda aqui. Eles mostram o que um agente que obedece a tudo o que lê pediria.

## Ajuda

Deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Não cole o contrato do seu agente inteiro, e nunca cole chave ou senha.
