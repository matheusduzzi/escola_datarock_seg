# 20. Dado pessoal e confidencial na IA

Os comandos da aula partem desta pasta. Você precisa do Python (3.9 ou mais novo). No Windows, troque `python3` por `py`.

O kit não chama modelo de IA nenhum e não abre conta nenhuma. Ele grava o log do atendimento da Loja Aurora com a máscara e procura o que sobrou.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `conversas.jsonl` | as 8 conversas de sexta de manhã, do jeito que chegaram ao assistente |
| `log-de-sexta.log` | o log que o assistente gravava antes da máscara |
| `atendimento.py` | grava o log de um arquivo de conversas, com a máscara aplicada antes de escrever |
| `mascara.py` | as regras da máscara: e-mail, CPF e telefone |
| `procurar.py` | procura num log o e-mail, o CPF, o telefone e o cartão que sobraram |
| `conversas-semana.jsonl` | as 13 conversas da semana seguinte, para o exercício |
| `minhas-respostas.md` | onde você responde o exercício |

## Rodar

```
python3 procurar.py log-de-sexta.log
python3 atendimento.py conversas.jsonl atendimento.log
python3 procurar.py atendimento.log
```

O `atendimento.py` sai com 0 quando grava e com 2 quando não consegue ler as conversas. Nesse caso, ele diz a linha com problema e não grava nada: nem um log pela metade, nem por cima do log que já existia.

O `procurar.py` sai com 0 quando não sobra nada, com 1 quando sobra e com 2 quando não consegue ler o arquivo (arquivo vazio, caminho errado). Ele mostra só os dois últimos números do que achou.

## As conversas

Uma conversa por linha, em JSON, com seis campos de texto:

| Campo | O que vai |
|---|---|
| `hora` | quando a conversa aconteceu |
| `canal` | `whatsapp` ou `formulario` |
| `cliente` | o código do cliente na loja, como `c-0412` |
| `pedido` | o número do pedido, ou vazio |
| `mensagem` | o que o cliente escreveu |
| `resposta` | o que o assistente respondeu |

A máscara roda só na mensagem e na resposta. Os outros campos são da loja e ficam no log como estão.

## O que o kit não faz

O `procurar.py` acha e-mail e fila de números. Ele não acha nome, endereço, doença nem um e-mail escrito por extenso ("arroba"). Saída 0 quer dizer que o que ele sabe procurar não sobrou. Uma pessoa ainda lê uma amostra do log.

## As suas respostas

```
cp minhas-respostas.md minhas-respostas-preenchidas.md      # macOS e Linux
copy minhas-respostas.md minhas-respostas-preenchidas.md    # Windows
```

O `.gitignore` deixa fora do git a cópia preenchida e os logs que você grava. Mesmo assim, nada de dado pessoal de verdade nas respostas.

Se travar, deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole CPF, telefone, e-mail ou número de cartão no comentário.
