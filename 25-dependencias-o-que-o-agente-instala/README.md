# 18. Dependências: o que o agente instala

Os arquivos da aula «Dependências: o que o agente instala». O projeto é a vitrine da Loja Aurora: um script em Node que o agente de código montou para o Diego e que gera a página de produtos a partir do catálogo.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `vitrine/` | o projeto, como o agente deixou: `package.json`, `package-lock.json`, `.gitignore`, `gerar.js`, `vitrine.js`, `catalogo.json`, os testes em `test/` e o `contrato-agente.csv` |
| `checar.py` | diz o que continua aberto nas dependências da vitrine: lockfile, versão com aviso, pacote de uma função, alerta, contrato e nome parecido |
| `avisos/` | o aviso GHSA-xvch-5gv4-984h no formato do banco OSV, que o `checar.py` usa sem internet |
| `registro.py` e `registro/` | o registro do curso: responde como o registro do npm, só para o pacote que o agente sugeriu |
| `pedido-do-agente.md` | a resposta do agente quando o Diego pediu para resolver a vulnerabilidade |
| `relatorio-diego.md` | o modelo do que você entrega no exercício |

## Sem instalar nada

Esses comandos rodam no seu computador e não baixam código. O Python 3.9 ou mais novo roda o `checar.py` e o registro. O Node e o npm leem o lockfile.

```
python3 checar.py
cd vitrine
npm ls --all --package-lock-only
npm audit --package-lock-only
```

O `npm audit` manda a lista de pacotes do lockfile para o registro do npm e recebe os avisos de volta. Ele precisa de internet e não instala nada.

O registro do curso roda num terminal separado:

```
python3 registro.py
```

Ele escuta em `http://127.0.0.1:4873` até você apertar Ctrl+C. Com a porta ocupada, use `python3 registro.py --porta 4874` e troque o número nos comandos. No outro terminal:

```
npm view minimist-safe --registry http://127.0.0.1:4873
```

## Instalar e testar só no contêiner

O `npm ci`, o `npm test` e qualquer `npm install` rodam dentro de um contêiner, como na aula «Sandbox de verdade». Assim o código que vem do npm não roda na sua máquina. De dentro da pasta `vitrine`:

```
docker run --rm -it -v "$PWD":/app -w /app node:24-slim bash
```

No Windows, no PowerShell, troque `"$PWD":/app` por `"${PWD}:/app"`.

Dentro do contêiner:

```
npm ci --ignore-scripts
npm test
```

A pasta `node_modules` aparece na sua pasta `vitrine`. O `.gitignore` deixa ela fora do git. Para sair do contêiner, `exit`.

## O que é de verdade e o que não é

O `minimist`, o `is-even` e os pacotes que vêm com ele existem no registro do npm. As versões do `package.json` e do lockfile são as que o registro mostrava em 09/11/2026, com o `integrity` de cada uma. O aviso GHSA-xvch-5gv4-984h também existe.

O `minimist-safe` não existe no npm. Ele só existe no registro do curso, sem código: o pedido do arquivo do pacote recebe 410 e nada se instala. Não instale esse nome de outro registro e não publique um pacote com ele. O mantenedor e o e-mail dele são inventados.

O `checar.py` não substitui o `npm audit`. Ele confere o lockfile contra o aviso guardado em `avisos/`, para funcionar sem internet. Aviso novo só aparece no `npm audit` e no alerta do GitHub.

No Windows, troque `python3` por `py`.

## Ajuda

Deixe um comentário na aula com o seu objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole token, senha ou dado pessoal no comentário.
