# 10. Guardrails de entrada e saída

Os arquivos da aula «Guardrails de entrada e saída: o que barram e o que deixam passar». Rode os comandos dentro desta pasta. As 15 mensagens da manhã ficam na pasta `mensagens/`, ao lado desta; os scripts leem de lá.

| Arquivo | O que é |
|---|---|
| `mensagem-16.json` | a 16ª mensagem da manhã, que chega com um print |
| `comprovante-pedido-4.png` | o print que vem com a mensagem 16 |
| `respostas-do-assistente.json` | o que o assistente sem defesa respondeu (`texto`) e fez (`acao`) para cada uma das 16 |
| `regras.json` | a lista de palavras, as regex e os sites permitidos do guardrail de regra fixa |
| `guardrail_regra.py` | o guardrail de regra fixa, na entrada ou na saída |
| `prompt-entrada.txt` e `prompt-saida.txt` | as instruções do classificador do guardrail com modelo |
| `guardrail_modelo.py` | o guardrail com modelo, na entrada ou na saída |
| `tabela.md` | o modelo da tabela do exercício |

## Regra fixa

```
python3 guardrail_regra.py entrada
python3 guardrail_regra.py saida
python3 guardrail_regra.py entrada --regras minhas-regras.json
```

Não precisa de internet nem de chave. Copie o `regras.json` como `minhas-regras.json` antes de mudar.

## Com modelo

Primeiro, conte as chamadas sem gastar nada:

```
python3 guardrail_modelo.py entrada --contar
```

Para rodar de verdade, você precisa de um modelo com API no formato de chat completions. Duas opções:

1. **Um provedor, com a chave do curso.** Crie uma chave só para essa aula, com teto de gasto e validade curta, e revogue no fim. Ela vai numa variável do terminal, nunca no código nem no chat:

   ```
   export GUARDRAIL_CHAVE=...
   python3 guardrail_modelo.py entrada --url https://<endereço do provedor>/v1 --modelo <nome do modelo> --salvar modelo-entrada.json
   ```

   No Windows (PowerShell), a variável é `$env:GUARDRAIL_CHAVE="..."`.

2. **Um modelo no seu computador**, pelo Ollama: `--url http://localhost:11434/v1`, sem chave.

Para o custo em dólar, passe os preços por milhão de tokens que a página do provedor mostra no dia: `--preco-entrada 0.15 --preco-saida 0.60` (troque pelos seus). A opção `--imagens` manda o print da mensagem 16 junto; use só com modelo que lê imagem.

Se o modelo não responder, ou responder fora do formato, o texto é barrado e a linha diz `erro`.

## No n8n

Quem usa o n8n pode montar o mesmo com o nó Guardrails, a partir da versão 1.119.0. A aula mostra a montagem. Cole os 16 textos no gatilho de chat, um por vez, e anote o resultado na tabela.

Nunca cole a chave, uma senha ou dado pessoal num comentário pedindo ajuda.
