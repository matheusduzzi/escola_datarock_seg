# Modelo de ameaça em uma página

Os arquivos dessa aula do curso Segurança no trabalho com IA. Não precisa instalar nada: são arquivos de texto em Markdown, com extensão `.md`, que abrem em qualquer editor.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `ficha-carla.md` | A ficha inicial da Carla, do financeiro da Loja Aurora, para a prática guiada |
| `modelo-de-ameaca.md` | A página em branco do exercício, com as cinco partes |

## Como usar

1. Faça a prática guiada da aula com a `ficha-carla.md`.
2. Salve uma cópia de `modelo-de-ameaca.md` e preencha as cinco partes.
3. Abra a sua ficha inicial, da pasta `00-apresentacao/`, e o seu quadro da pasta `01-novo-cenario/`. O exercício parte dos dois.
4. Guarde a página junto deles. Ela volta nas próximas aulas e no projeto final.

A aula mostra três comandos opcionais. Rode da pasta dessa aula; os arquivos que eles leem estão nas pastas `loja-aurora/` e `00-apresentacao/` do kit:

```
grep -n "url.path" ../loja-aurora/app.py
grep -n "aurora_sk" ../00-apresentacao/material/conversa-equipe.txt ../00-apresentacao/material/config-do-site.js
cd ../loja-aurora && python3 sondar.py
```

No Windows, abra os arquivos no editor e procure pelo texto entre aspas. O `sondar.py` sai com `1` enquanto houver falha aberta no app; no começo do curso, todas estão abertas.

A sua página fala do seu trabalho. Se for mostrar num comentário, tire nomes de pessoas, de empresas, de ferramentas internas e qualquer chave.

## Ajuda

Deixe um comentário na aula com o seu objetivo, o que você fez, o que apareceu e o que já tentou. Use os dados do caso, sem dados pessoais.
