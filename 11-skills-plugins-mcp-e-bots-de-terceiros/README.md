# Aula 12: Skills, plugins, MCP e bots de terceiros

Arquivos dessa aula. Os comandos partem desta pasta.

| Arquivo | O que é |
|---|---|
| `listar_skill.py` | lista os arquivos de uma skill e as linhas que pedem leitura; só lê, não roda nada da skill |
| `skill-etiquetas-envio/` | a skill da prática guiada |
| `skill-resumo-pedidos/` | a skill do exercício |
| `pedidos.csv` | os cinco pedidos que as duas skills leem |
| `revisao-skill.md` | modelo da revisão de uma skill |
| `ficha-extensao.md` | modelo da ficha de uma extensão que você usa e do app de teste que você revoga |

```
python3 listar_skill.py skill-etiquetas-envio
python3 listar_skill.py skill-resumo-pedidos
```

As duas skills existem só no curso. **Não copie nenhuma delas para `~/.claude/skills/` nem para `.claude/skills/`**: a ideia é revisar antes de instalar, e a do exercício tem um problema de propósito. Os endereços com final `.invalid` não existem na internet.

No Windows, troque `python3` por `py`.
