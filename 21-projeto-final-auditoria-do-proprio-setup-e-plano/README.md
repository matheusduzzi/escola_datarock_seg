# Projeto final: auditoria do próprio setup e plano de incidente

Os arquivos da última aula do curso Segurança no trabalho com IA. Você precisa do Python 3.9 ou mais novo, o mesmo do resto do curso. Nada para instalar.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `auditoria.md` | O modelo da auditoria do seu setup, em seis partes |
| `plano-de-incidente.md` | O modelo do plano de uma página para quando uma chave vazar |
| `ensaio.py` | O vazamento de mentira da Loja Aurora, em duas fases, para ensaiar o plano |

## Como usar

1. Salve uma cópia de `auditoria.md` e de `plano-de-incidente.md` e preencha as duas.
2. Abra um terminal nessa pasta e rode `python3 ensaio.py comecar`. Ele monta a pasta `cena/` e mostra o primeiro aviso.
3. Siga o seu plano, passo a passo, com os comandos abaixo. Anote o que o plano não dizia.
4. Quando `python3 ensaio.py checar` sair com 0, rode `python3 ensaio.py segunda-fase` e ensaie de novo.

```
python3 ensaio.py comecar              # monta cena/ e mostra o primeiro aviso
python3 ensaio.py chaves               # as chaves da loja, mascaradas, e onde cada uma está
python3 ensaio.py guardar              # copia avisos e registros para cena/provas/, com o hash
python3 ensaio.py trocar NOME --gravar hospedagem.env
python3 ensaio.py instalar NOME --em ci.env
python3 ensaio.py checar               # sai 1 enquanto algo está aberto e 0 quando a fase fecha
python3 ensaio.py segunda-fase         # o segundo aviso
python3 ensaio.py comecar --de-novo    # apaga cena/ e começa do zero
```

No Windows, troque `python3` por `py`.

## A cena

Tudo acontece dentro de `cena/`. Os arquivos `hospedagem.env`, `ci.env` e `oauth.env` fazem o papel dos painéis onde a loja configura as chaves. As chaves são da loja do curso e não abrem conta nenhuma. A chave nova nunca aparece na tela, só os 4 últimos caracteres.

O `ensaio.py` só mexe em `cena/`. A pasta `cena/` está no `.gitignore` dessa aula.

## Ajuda

Se travar, deixe um comentário na aula com o seu objetivo, o comando que rodou, a saída e o que já tentou. Nunca cole uma chave, senha ou dado pessoal no comentário.
