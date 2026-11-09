# Plano de incidente: quando uma chave vazar

Uma página. Se não couber, corte explicação, não corte passo. Escreva nomes de pessoas e de painéis, não cargos genéricos.

Setup de: ______________________  Versão: ____  Última vez ensaiado em: ____/____/______

## 1. Quem faz o quê

| Papel | Quem | Contato fora do e-mail da empresa | Substituto |
|---|---|---|---|
| Decide (para tudo, tira do ar, gasta) | | | |
| Troca as chaves | | | |
| Fala com o provedor (gateway, nuvem, hospedagem) | | | |
| Leva ao jurídico e cuida da comunicação de dado pessoal | | | |
| Avisa equipe e clientes | | | |

## 2. Primeiros 15 minutos

1. Anote a hora em que você soube. Ela conta para o prazo de comunicação, se houver dado pessoal.
2. Guarde as provas antes de limpar qualquer coisa (seção 4).
3. Considere vazado tudo o que estava no mesmo arquivo, print ou conversa, não só a chave do aviso.
4. Troque as chaves na ordem da seção 3. Revogar vem antes de apagar o post, o comentário ou o histórico.
5. Procure cada cópia da chave velha: hospedagem, CI, `.env` de cada pessoa, automações, cofre.

## 3. O que troco, em que ordem, e onde cada uma está

Do maior prejuízo para o menor. Ponha no fim só o que tem teto de gasto ou não abre dado.

| Ordem | Chave ou acesso | O que alguém faz com ela | Onde está configurada (todas as cópias) | Onde se revoga | Quem testa depois |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

O que costuma ficar esquecido (marque o que você tem): [ ] token de CI  [ ] deploy hook  [ ] app autorizado por OAuth  [ ] chave copiada num teste  [ ] chave no `.env` de outra pessoa

## 4. O que guardo como prova, e onde

| Prova | Onde fica guardada | Quem pode abrir |
|---|---|---|
| O aviso (e-mail, alerta, mensagem) com data e hora | | |
| Cópia do lugar onde a chave apareceu | | |
| Registro de uso da chave no painel do provedor | | |
| Linha do tempo: o que foi feito, por quem, a que horas | | |

## 5. Se o provedor que guarda os segredos for o invadido

- O que troco primeiro, já que tudo o que estava lá vale como vazado:
- Se ele pausar os deploys e a chave nova não chegar ao app, o que a loja faz até lá:

## 6. Dado pessoal

- Se o registro mostrar acesso a dado de cliente, quem leva ao jurídico e em quanto tempo:
- Onde fica o registro do incidente, mesmo que ele não precise ser comunicado:

## 7. Depois do ensaio

- O que o ensaio mostrou que este plano esqueceu:
- O que mudei no plano por causa disso:
