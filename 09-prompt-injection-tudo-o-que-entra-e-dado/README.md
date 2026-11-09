# 09. Prompt injection: tudo o que entra é dado

Os arquivos da aula «Prompt injection: tudo o que entra é dado». Rode os comandos dentro desta pasta. As 15 mensagens da manhã ficam na pasta `mensagens/`, ao lado desta; o script lê de lá.

| Arquivo | O que é |
|---|---|
| `montar_contexto.py` | mostra o que o assistente recebe para uma mensagem, e o que a pessoa vê na tela |
| `prompt-do-assistente.txt` | as instruções que a loja escreveu para o assistente, com a linha que o Diego acrescentou |
| `ferramentas.txt` | as ferramentas que o assistente alcança hoje, sem defesa |
| `tarde.json` | os três textos da tarde, usados na prática guiada |
| `classificacao.md` | o modelo da tabela do exercício |

## Como usar

```
python3 montar_contexto.py 6            # o que vai para o modelo com a mensagem 6
python3 montar_contexto.py 6 --pessoa   # o que a pessoa da equipe vê na caixa de entrada
python3 montar_contexto.py G1           # um dos textos da tarde
```

Precisa só do Python 3.9 ou mais novo. Não chama modelo nenhum e não precisa de internet nem de chave. No Windows, troque `python3` por `py`.

Para o exercício, copie `classificacao.md` como `minha-classificacao.md` e preencha.

Se travar, deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole uma chave, senha ou dado pessoal no comentário.
