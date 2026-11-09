# 05. Cofre de senhas e contas próprias para o agente

Os comandos da aula partem desta pasta. Você precisa do Python (3.9 ou mais novo). No Windows, troque `python3` por `py`.

O kit não abre gerenciador de senhas nenhum. Ele lê o desenho dos cofres, que você escreve num CSV, e mostra o que cada pessoa e cada agente alcança.

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `alcance.py` | lê um desenho e mostra quem alcança o quê, o que cai se um cofre ou uma credencial vazar e os problemas do desenho |
| `exemplos/atalho.csv` | a proposta do Diego para o atendimento: um cofre para todos e uma chave para todos os apps |
| `exemplos/contas-proprias.csv` | o desenho que a Renata aprovou, com um cofre por pessoa e as contas do assistente |
| `diego-hoje.csv` | os cofres do Diego hoje, para o exercício |
| `desenho-modelo.csv` | o cabeçalho do desenho, para copiar |
| `minhas-respostas.md` | onde você responde o exercício |

## Rodar

```
python3 alcance.py exemplos/atalho.csv
python3 alcance.py exemplos/contas-proprias.csv
```

O `alcance.py` sai com 0 quando não acha problema, com 1 quando acha e com 2 quando não consegue ler o arquivo (cabeçalho errado, arquivo vazio, campo a mais).

## O desenho

Copie o modelo e abra no editor de texto ou na planilha (salvando como CSV):

```
cp desenho-modelo.csv meu-cofre.csv          # macOS e Linux
copy desenho-modelo.csv meu-cofre.csv        # Windows
python3 alcance.py meu-cofre.csv
```

Uma linha por item. As colunas:

| Coluna | O que vai |
|---|---|
| `cofre` | o nome do cofre, ou da coleção, onde o item fica |
| `dono` | a pessoa que responde pelo cofre. Uma pessoa, com nome; nunca um agente nem "equipe" |
| `quem_acessa` | quem abre o cofre, separado por `;`. Agente leva `agente:` na frente: `agente:assistente` |
| `item` | o nome do item: `senha do e-mail contato@`, `chave de IA do assistente …t1Wx`. Nunca o valor |
| `tipo` | `senha`, `chave`, `token`, `cartao`, `cartao-virtual` ou `nota` |
| `de_quem` | de quem é a conta: a pessoa, a empresa ou o agente (`agente:assistente`) |
| `limite` | só para cartão virtual: o limite, como `R$ 250 por dia`. Vazio nos outros |
| `alcance` | o que dá para fazer com o item, separado por `;`: `cobrar; estornar; ver clientes` |

Todas as linhas do mesmo cofre repetem o `dono` e o `quem_acessa`. Quando duas linhas abrem a mesma coisa, escreva do mesmo jeito: o `alcance.py` junta pelo texto.

O `alcance.py` reclama de:

- cofre que um agente divide com outra pessoa ou outro agente;
- cartão num cofre que um agente abre;
- cartão virtual sem limite;
- agente usando conta que não é dele;
- o mesmo item em dois cofres;
- dono vago ("equipe", "todos", "loja") ou agente como dono;
- coluna vazia, tipo que não existe e qualquer coisa com cara de senha, chave ou número de cartão.

Ele lê o que você escreveu e não sabe se é verdade. Se você marca a chave do gateway como do agente, ele acredita.

Texto com vírgula vai entre aspas, como `"provedor de IA: até US$ 2,00 por dia"`. A planilha faz isso sozinha quando você salva como CSV.

Os nomes, contas e valores da Loja Aurora são da loja do curso. Mesmo assim, o hábito vale: nada de valor de senha, chave ou cartão no desenho.

## Ajuda

Deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Não cole o seu desenho de verdade nem nenhuma senha, chave ou número de cartão.
