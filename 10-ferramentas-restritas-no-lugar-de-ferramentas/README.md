# 11. Ferramentas restritas no lugar de ferramentas cruas

Os arquivos da aula «Ferramentas restritas no lugar de ferramentas cruas». Rode tudo dentro dessa pasta, com o Python 3.9 ou mais novo. Não precisa instalar nada, nem de internet, nem de chave. As 15 mensagens da manhã ficam na pasta `mensagens/`, na raiz do kit; o script lê de lá.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `assistente.py` | a casca do assistente: decide quem escreveu, o que chega ao modelo, que ferramenta roda e para onde vai a resposta |
| `config/atendimento-antes.json` | o assistente do atendimento como o Diego montou: terminal, SQL, e-mail e página |
| `config/atendimento-depois.json` | o mesmo assistente com cinco ferramentas estreitas e a lista de remetentes |
| `config/equipe-antes.json` | o assistente interno da equipe, do exercício, ainda com terminal, SQL e e-mail |
| `canais.json` | o que o canal diz de cada mensagem da manhã: o número do WhatsApp, o e-mail, de onde veio o anexo |
| `roteiro/` | o que o modelo pede em cada mensagem, com as ferramentas cruas e com as estreitas |
| `equipe/` | as 8 mensagens da tarde do exercício, o canal de cada uma e a lista de contatos da equipe |
| `loja/` | os documentos da loja que a busca lê e o `.env` com a chave do gateway |
| `minhas-respostas.md` | o modelo das respostas do exercício |

## Os comandos

```
python3 assistente.py rodar config/atendimento-antes.json
python3 assistente.py rodar config/atendimento-depois.json
python3 assistente.py comparar config/atendimento-antes.json config/atendimento-depois.json
python3 assistente.py checar config/atendimento-depois.json
python3 assistente.py chamar config/atendimento-depois.json ver_pedidos numero=1 --de bia@cliente.example
```

- `rodar` passa as mensagens pela casca. Para cada uma, mostra o papel de quem escreveu, cada ferramenta pedida, o que a casca fez com o pedido e as linhas com ⚠ quando algo ruim aconteceu. No fim, mostra o que mudou na loja. Sai com `1` se alguma mensagem teve ⚠ e com `0` se nenhuma teve.
- `comparar` roda duas configurações e mostra o antes e o depois numa tabela, mensagem por mensagem.
- `checar` lê uma configuração e lista os problemas: ferramenta crua, ferramenta liberada para quem não devia, remetente só com nome, campo livre de agente. Sai com `1` se achar algum.
- `chamar` faz uma chamada só, como se a mensagem viesse de quem você puser em `--de`. Serve para testar uma ferramenta com um argumento estranho.

No Windows, troque `python3` por `py`.

O `assistente.py` cria o `loja.db` na pasta em que você roda e recria a cada `rodar`, com os pedidos do começo. O `.gitignore` deixa o banco de fora do git, junto com os arquivos que você cria na prática e no exercício.

## As ferramentas

As cruas, que a aula tira:

| Ferramenta | O que faz |
|---|---|
| `terminal` | roda um comando na pasta da loja |
| `sql` | roda qualquer SQL no banco da loja |
| `enviar_email` | manda e-mail para qualquer endereço, na hora |
| `abrir_pagina` | abre qualquer página da internet |

As estreitas, que entram no lugar:

| Ferramenta | Argumentos | O que faz |
|---|---|---|
| `buscar_documento` | `termo` | procura o termo só nos arquivos de `loja/documentos` |
| `ver_pedidos` | `numero` (opcional) | mostra os pedidos de quem escreveu; o e-mail vem do canal, não do modelo |
| `abrir_chamado` | `tipo`, `numero`, `detalhe` | abre um chamado de troca, cancelamento, endereço ou nota fiscal num pedido de quem escreveu |
| `marcar_coleta` | `dia`, `hora` | marca a coleta da transportadora na agenda do assistente |
| `criar_rascunho` | `texto` | escreve a resposta para quem mandou a mensagem; uma pessoa lê antes de sair |
| `resumo_vendas` | nenhum | quantidade e total dos pedidos pagos, por categoria |
| `ver_pedido_da_loja` | `numero` | mostra um pedido qualquer, pelo número; só para a equipe |

## O formato da configuração

```
{
 "nome": "...",
 "mensagens": "...", "canais": "...", "roteiro": "...",
 "prompt": "...",
 "ferramentas": {"ver_pedidos": ["cliente"], "criar_rascunho": ["todos"]},
 "remetentes": {
  "equipe": [{"nome": "Carla", "email": "carla@aurora.example", "whatsapp": "(19) 90000-0002"}],
  "contatos": [{"nome": "Rota Sul", "email": "coletas@rotasul.example", "papel": "transportadora"}],
  "agentes": {"triagem": ["cliente", "assunto", "prioridade"]},
  "desconhecido": "atende"
 }
}
```

- `ferramentas`: cada ferramenta com a lista de papéis que podem usar. Os papéis são `cliente`, `equipe`, `transportadora`, `contador`, `agente` e `desconhecido`, ou `todos`.
- `remetentes`: quem é quem, pelo e-mail ou pelo WhatsApp. Cliente é quem está no cadastro da loja. Formulário do site é sempre `desconhecido`, porque o nome e o e-mail ali qualquer um digita.
- `agentes`: os campos do resumo de outro agente que passam para o modelo. O resto fica de fora.
- `desconhecido`: `atende` responde com as ferramentas liberadas para `desconhecido`; `barra` faz a mensagem nem chegar ao modelo.
- Com `criar_rascunho` na lista, toda resposta vira rascunho. Sem ela, a resposta sai na hora.

## O que é de verdade e o que não é

O banco é um SQLite com os mesmos clientes e pedidos da Loja Aurora. As ferramentas gravam nele de verdade: um estorno vira uma linha em `estornos`, uma mensagem enviada vira uma linha em `enviados`, um rascunho vira uma linha em `rascunhos`. As linhas com ⚠ saem do banco e do que saiu da loja, não do roteiro.

O terminal do kit não roda nada no seu computador. Ele imita `ls`, `cat` e `grep` dentro da pasta `loja/`, e responde o resto com um aviso. Num terminal de verdade, qualquer comando rodaria.

Os arquivos de `roteiro/` foram escritos à mão. Nenhum modelo de IA roda aqui. Eles mostram o que um assistente que obedece a tudo o que lê pediria. Quando a ordem plantada não chega ao modelo, o passo que dependia dela não acontece, e a saída diz isso.

A chave do `loja/.env` e os e-mails têm o formato do curso e não abrem conta nenhuma.

## Ajuda

Deixe um comentário na aula com o objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole uma chave, senha ou dado pessoal no comentário.
