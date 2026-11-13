# Aula 19: Auditoria antes de publicar

Essa pasta tem a Loja Aurora num repositório git, com o PR da Sexta Aurora que o agente do Diego escreveu. E tem as ferramentas da auditoria. Você precisa do Python (3.9 ou mais novo) e do git. Os comandos partem dessa pasta. No Windows, troque `python3` por `py`.

```
python3 montar.py                        # cria repo-aurora/, com a main e a branch cupom-sexta (o PR)
python3 montar.py --de-novo              # apaga repo-aurora/ e começa do zero
python3 portao.py repo-aurora            # o portão do PR: segredos, dependências, código e testes
python3 checar.py repo-aurora            # os sete itens da auditoria: sai 1 enquanto algum estiver aberto
python3 sast.py repo-aurora              # só as regras de código, numa pasta
python3 achar_segredos.py repo-aurora --historico   # o detector de chaves da aula 03, em todos os commits
python3 pedir.py caio /api/clube/guia    # teste à mão, com a loja aberta (veja abaixo)
```

O `portao.py` e o `checar.py` olham a branch atual do `repo-aurora` contra a `main`. Para olhar outra, use `--branch nome-da-branch`. Os dois copiam os arquivos da branch para uma pasta temporária. Lá, sobem a loja numa porta livre do seu computador, com banco novo, e apagam tudo no fim.

## O que tem aqui

| Arquivo | O que é | Você mexe? |
|---|---|---|
| `montar.py` | monta o `repo-aurora/` com a `main` (a pasta `loja/`) e o PR em três commits (a pasta `pr-cupom-sexta/`) | não |
| `loja/` e `pr-cupom-sexta/` | os arquivos que o `montar.py` põe no repositório | não: mexa no `repo-aurora/` |
| `portao.py` | faz o papel do CI: as quatro etapas que barram o PR | não |
| `achar_segredos.py` | o detector de chaves da aula «Segredos fora do código, do chat e da tela», o mesmo arquivo | não |
| `sast.py` | as regras de código, no papel de um SAST como o Semgrep | não |
| `avisos/` | o aviso de falha do PyYAML, copiado do banco público OSV (osv.dev) em 09/11/2026 | não |
| `checar.py` | os sete itens da auditoria, com o relógio da loja parado em horários escolhidos | não |
| `pedir.py` | entra com uma conta de teste e faz um pedido para a loja aberta | não |
| `regras-da-loja.md` | as regras da Sexta Aurora, como a Renata escreveu | não |
| `checklist.md` | as perguntas fixas antes de publicar | não |
| `revisor/escopos.md` | os cinco escopos do revisor, uma rodada por escopo | não |
| `revisor/revisor-seguranca.md` | um subagente só de leitura para o Claude Code | copie para `.claude/agents/` se for usar |
| `ci/portao.yml` | o mesmo portão no GitHub Actions, para um repositório seu | copie para `.github/workflows/` no seu repositório |
| `relatorio-auditoria.md` | o modelo do relatório | copie como `meu-relatorio.md` |

## A loja dentro do repositório

```
cd repo-aurora
git log --oneline --all       # a main e os três commits do PR
python3 app.py                # abre a loja em http://127.0.0.1:8765; Ctrl+C para parar
python3 -m unittest           # os testes da branch
```

Com a loja aberta, use outro terminal na pasta da aula para os testes à mão da checklist: `python3 pedir.py CONTA CAMINHO`, com a conta `bia`, `caio`, `duda`, `renata` ou `ninguem` (sem login).

| Conta | Senha | Papel | Plano |
|---|---|---|---|
| `bia@cliente.example` | `Bia#teste1` | cliente | Clube |
| `caio@cliente.example` | `Caio#teste2` | cliente | grátis |
| `duda@cliente.example` | `Duda#teste3` | cliente | grátis |
| `renata@aurora.example` | `Renata#teste4` | admin | grátis |

Os nomes, e-mails e pedidos são inventados, e o domínio `example` não entrega mensagem para ninguém. As chaves do repositório têm o formato `aurora_..._` e não abrem conta nenhuma. O curso trata todas como se fossem de verdade.

## As ferramentas de verdade

O `portao.py`, o `sast.py` e o `achar_segredos.py` fazem, sem internet, o papel de ferramentas que você usa num repositório seu: o gitleaks (segredos), o pip-audit (dependências) e o Semgrep Community Edition (código). O `ci/portao.yml` chama essas três no GitHub Actions. Elas têm mais regras que as do kit e vão apontar outras coisas: cada achado novo passa pela mesma triagem.

## A regra do curso

Tudo dessa aula roda na Loja Aurora, no seu computador. O `pedir.py` só fala com `127.0.0.1`. Não rode scanner, revisor nem teste à mão em site, app ou repositório de outra pessoa ou empresa, nem "só para ver". O app não deve ser publicado.

Para pedir ajuda, deixe um comentário na aula com o objetivo, o comando, a saída e o que já tentou. Nunca cole chave, token, senha ou dado pessoal.
