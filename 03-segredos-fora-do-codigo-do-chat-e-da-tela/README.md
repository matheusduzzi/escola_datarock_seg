# 03. Segredos fora do código, do chat e da tela

Os comandos da aula partem desta pasta. Você precisa do Python (3.9 ou mais novo) e do git. No Windows, troque `python3` por `py`.

```
python3 montar.py            # cria repo-aurora/, repo-assistente/ e painel.json
python3 montar.py --de-novo  # apaga os três e começa do zero
```

## O que tem aqui

| Arquivo | O que faz |
|---|---|
| `montar.py` | monta os dois repositórios git da Loja Aurora, com o histórico que a equipe deixou, e o painel de chaves |
| `achar_segredos.py` | procura chaves numa pasta (`python3 achar_segredos.py dist`) ou em todos os commits (`--historico`); mostra só o prefixo e os 4 últimos caracteres e sai com 1 quando acha chave secreta |
| `painel.py` | faz o papel da página de chaves do gateway e do provedor de IA: `listar`, `revogar --final XXXX` e `nova`, que grava a chave direto no `.env` sem mostrar |
| `checar.py` | diz quais dos seis itens da aula estão fechados num repositório (`python3 checar.py repo-aurora`) |
| `minhas-respostas.md` | onde você responde o exercício |

O `repo-aurora` é o site da loja, usado na aula e na prática guiada. O `repo-assistente` é o assistente de produtos da Carla, usado no exercício. Dentro de cada um:

```
python3 build.py      # monta dist/, o que vai para o navegador
python3 servidor.py   # site em 127.0.0.1 (8790 no site, 8791 no assistente); Ctrl+C para parar
```

As chaves dos repositórios e do painel são da loja do curso e não abrem conta nenhuma. Mesmo assim, o curso trata todas como se fossem de verdade: nada de colar no chat nem mostrar na tela.

## Variável do sistema na frente do comando

O `config.py` dos repositórios lê o `.env` e, por cima, as variáveis do sistema, que fazem o papel do host.

```
PUBLIC_LOJA_NOME="Loja Aurora (teste)" python3 build.py         # macOS e Linux
$env:PUBLIC_LOJA_NOME="Loja Aurora (teste)"; py build.py        # Windows, PowerShell
```

No PowerShell, a variável fica valendo até você fechar a janela.

## Editar arquivos

Os passos que mudam o `.gitignore`, o `.env` e o `pagamento.py` podem ser feitos no seu editor de texto. O `.gitignore`, o `.env` e o `.dockerignore` começam com ponto e às vezes ficam escondidos: no Finder, Command+Shift+. mostra; no Explorador do Windows, marque "Itens ocultos".

## Ajuda

Deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Troque qualquer chave por `...` antes de colar.
