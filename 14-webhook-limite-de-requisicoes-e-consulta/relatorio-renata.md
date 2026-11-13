# O que o app expõe e o que eu mudei

Copie este arquivo como `meu-relatorio.md` e preencha. Não cole token, segredo nem dado pessoal.

## 1. As rotas do app

Uma linha por rota do `app.py`, as que o site usa e as que ele não usa. Procure `url.path` no arquivo.

| Método e rota | Quem chama | O que ela exige antes de agir | Limite | O que eu decidi (manter, fechar, desligar) |
|---|---|---|---|---|
| `GET /api/produtos` | | | | |
| | | | | |

## 2. As nove checagens

| Checagem | O que um robô ou curioso conseguia | Onde estava (arquivo e função) | O que eu mudei | Linha do `checar.py` depois |
|---|---|---|---|---|
| busca-concatenada | | | | |
| ordem-e-limite | | | | |
| erro-com-detalhe | | | | |
| webhook-sem-segredo | | | | |
| webhook-repetido | | | | |
| webhook-esquecido | | | | |
| cadastro-em-massa | | | | |
| modelo-sem-login | | | | |
| modelo-sem-limite | | | | |

Se você faz pela checklist, troque a coluna "O que eu mudei" por "O que eu peço para quem programa".

## 3. A frase para o agente

A frase que o Diego passa a pôr no pedido ao agente quando ele cria uma rota nova:

>
