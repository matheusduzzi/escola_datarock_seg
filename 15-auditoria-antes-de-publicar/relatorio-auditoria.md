# Auditoria do PR «Sexta Aurora» antes de publicar

Copie este arquivo como `meu-relatorio.md` e preencha. Não cole chave, token, senha nem dado de cliente: para uma chave, escreva só o começo e os 4 últimos caracteres, como o portão mostra.

- Quem fez a auditoria:
- Data:
- Branch auditada e commits (`git log --oneline main..cupom-sexta`):
- O que eu rodei: checklist (itens), portão, rodadas do revisor (quais, com que ferramenta e modelo, ou com que pessoa)

## 1. Achados

Uma linha por achado, inclusive o falso positivo e o que virou aceite de risco.

| # | Achado | Quem achou (checklist e item, portão e etapa, revisor e rodada, pessoa) | Onde (arquivo e função ou commit) | Decisão: corrigido, falso positivo ou aceite de risco | O que eu mudei, ou a justificativa | A prova depois (linha do portão, do `checar.py` ou teste) |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

## 2. Falso positivo

Para cada achado que não é falha, escreva quatro coisas. O que a ferramenta apontou. Por que não é falha. O trecho da documentação que mostra isso, com o endereço e a data. E como você marcou o código para a próxima rodada saber.

## 3. Aceite de risco

| Risco | O que pode acontecer | Por que não corrige antes de publicar | Dono | Prazo | O que segura o risco enquanto isso | O que faz o item voltar antes do prazo |
|---|---|---|---|---|---|---|
| | | | | | | |

## 4. O que o automático não pegou e uma pessoa pegou

Para cada achado que o portão (segredos, dependências, código e testes) não apontou: o que era, quem achou, com que pergunta, e por que a ferramenta não tinha como ver.

## 5. As rodadas do revisor

| Rodada | Ferramenta e modelo, ou pessoa | O que apontou | O que eu mostrei com pedido ou teste | Virou achado? |
|---|---|---|---|---|
| | | | | |

## 6. Antes do merge

- Saída final do `python3 portao.py repo-aurora`:
- Saída final do `python3 checar.py repo-aurora`:
- A frase que o Diego passa a pôr no pedido ao agente quando ele mexe em regra de negócio:
