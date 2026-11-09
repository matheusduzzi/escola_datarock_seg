# Aula 08. Sandbox de verdade

Os comandos partem desta pasta. Você precisa do Docker rodando (Docker Desktop no Mac e no Windows, Docker Engine no Linux). No Windows, rode no terminal do WSL2 ou troque `$PWD` por `${PWD}` no PowerShell.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `Dockerfile` | a imagem do contêiner: Python, os programas abaixo e, se você pedir, um agente de código |
| `alcance.py` | lista o que o processo alcança e o que não alcança: arquivos, variáveis e rede. Nunca mostra conteúdo nem valor |
| `agente_roteiro.py` | faz o que um agente que obedece a uma instrução plantada faria. Não tem modelo de IA |
| `porta_de_saida.py` | o proxy que só deixa sair para os endereços de `permitidos.txt` e anota cada tentativa |
| `permitidos.txt` | a lista da porta. Começa só com `api.anthropic.com` |
| `coletor.py` | faz o papel do servidor de fora, que recebe o que vazou. Mostra nome e tamanho, nunca o conteúdo |
| `projeto/` | a pasta que o agente recebe: a tarefa, as notas do tema com a instrução plantada, um `.env` com chaves de teste e pedidos de teste |
| `casa-do-diego/` | a pasta de usuário do Diego como ela é no computador dele: chave SSH, credencial de nuvem e o `.env` de produção. Tudo é texto do curso e não abre conta nenhuma |
| `exercicio/comando-novo.sh` | o segundo comando do Diego, para o exercício |
| `minhas-respostas.md` | o modelo para as suas respostas |

Os dois `.env` desta pasta ficam no repositório de propósito: são do curso. O `.gitignore` daqui abre exceção só para eles.

## Preparar (uma vez)

```
docker build -t aurora-sandbox .
docker network create aurora-aberta
docker network create --internal aurora-fechada
docker run -d --rm --name coletor --network aurora-aberta aurora-sandbox python3 /kit/coletor.py
```

A rede `aurora-aberta` sai para a internet. A `aurora-fechada` foi criada com `--internal`: quem está só nela não sai para lugar nenhum.

## Passo 1. Do jeito do Diego

```
docker run --rm --network aurora-aberta \
  -v "$PWD/casa-do-diego:/home/node" \
  -v "$PWD/projeto:/trabalho" \
  --env-file casa-do-diego/projetos/loja-aurora/.env \
  aurora-sandbox

docker run --rm --network aurora-aberta \
  -v "$PWD/casa-do-diego:/home/node" \
  -v "$PWD/projeto:/trabalho" \
  --env-file casa-do-diego/projetos/loja-aurora/.env \
  aurora-sandbox python3 /kit/agente_roteiro.py

docker logs coletor
```

## Passo 2. Sem internet

```
docker run --rm --network none --read-only --tmpfs /tmp \
  --cap-drop ALL --security-opt no-new-privileges \
  -v "$PWD/projeto:/trabalho" \
  aurora-sandbox
```

Troque o fim por `aurora-sandbox python3 /kit/agente_roteiro.py` para ver a tentativa de envio.

## Passo 3. Saída só pela porta

```
mkdir -p registro
docker run -d --rm --name porta --network aurora-aberta \
  -v "$PWD/permitidos.txt:/kit/permitidos.txt:ro" \
  -v "$PWD/registro:/registro" \
  aurora-sandbox python3 /kit/porta_de_saida.py
docker network connect aurora-fechada porta

docker run --rm --network aurora-fechada \
  -e HTTPS_PROXY=http://porta:3128 -e HTTP_PROXY=http://porta:3128 \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
  -v "$PWD/projeto:/trabalho" \
  aurora-sandbox

docker logs porta
cat registro/saida.jsonl
```

Rode também o `agente_roteiro.py` do mesmo jeito. Se você mudar o `permitidos.txt`, pare a porta (`docker stop porta`) e suba de novo. Se o `cat` der erro de permissão no Linux, o `docker logs porta` mostra as mesmas linhas.

## Passo 4. O seu agente no contêiner

Para o Claude Code, a imagem instala o agente com o pacote da documentação:

```
docker build --build-arg AGENTE=@anthropic-ai/claude-code -t aurora-sandbox-claude .
```

Crie uma chave de API só para o curso, com teto de gasto e validade curta, e deixe ela numa variável do terminal, sem gravar em arquivo. Depois:

```
docker run --rm -it --network aurora-fechada \
  -e HTTPS_PROXY=http://porta:3128 -e HTTP_PROXY=http://porta:3128 \
  -e ANTHROPIC_API_KEY -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  --read-only --tmpfs /tmp --tmpfs /home/node \
  --cap-drop ALL --security-opt no-new-privileges \
  -v "$PWD/projeto:/trabalho" \
  aurora-sandbox-claude claude
```

O `-e ANTHROPIC_API_KEY` sem valor passa para o contêiner a variável que já está no seu terminal. Na primeira vez, o Claude Code pede para você aprovar o uso da chave.

Outro agente: troque o pacote no `docker build` (o Codex, por exemplo, é `@openai/codex`), a variável da chave e o endereço do modelo no `permitidos.txt`. Antes, veja na documentação dele se ele respeita `HTTPS_PROXY`. Se não respeitar, ele não fala com o modelo, e a porta mostra isso no registro.

Sem agente de código ou sem chave: faça o Passo 4 com o `agente_roteiro.py`, como no Passo 3.

## Encerrar

```
docker stop porta coletor
docker network rm aurora-aberta aurora-fechada
```

## Rodar fora do Docker

`python3 alcance.py` roda no seu computador também. É o jeito mais rápido de ver o que um agente rodando direto na sua máquina alcança. Os outros programas rodam igual, mas sem contêiner nada fica isolado.

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole a chave, o `.env` ou o conteúdo do `registro/` com dados seus.
