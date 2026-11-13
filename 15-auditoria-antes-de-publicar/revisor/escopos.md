# O revisor por escopo: cinco rodadas

Uma rodada olha um assunto só. Pedir "revise a segurança do PR" de uma vez dá uma lista genérica e esquece o que não é padrão conhecido. Faça uma rodada por escopo, com um agente de IA ou com uma pessoa. Anote no relatório o que cada rodada apontou e o que você mostrou com um pedido ou um teste.

## Antes da primeira rodada

1. Gere o diff do PR dentro de `repo-aurora`: `git diff main...cupom-sexta > ../pr.diff`. O revisor lê esse arquivo e os arquivos que o diff cita.
2. Se for um agente de IA, use um que a sua empresa aprovou para receber código. O código vai sem `.env`, sem chave e sem dado de cliente.
3. Deixe o agente só com leitura. No Claude Code, o arquivo `revisor-seguranca.md` desta pasta é um subagente com as ferramentas Read, Grep e Glob: ele lê e procura, não edita nem roda comando. Para o `.env` ficar fora de alcance, a configuração de permissões do Claude Code aceita a regra `"deny": ["Read(./.env)", "Read(./.env.*)"]`.
4. Cole o texto comum e depois o texto da rodada.

## O texto comum de toda rodada

```
Você é um revisor de segurança. Revise SÓ o escopo abaixo, no PR do arquivo pr.diff
e nos arquivos que ele cita. Não abra .env nem nada fora da pasta. Não mude nenhum arquivo.
Para cada problema: arquivo e linha, o que um cliente comum ou um atacante consegue fazer,
um pedido ou teste que mostra o problema, e a correção. Se não achar nada no escopo,
responda "nada neste escopo" e diga o que você leu.
```

## Rodada 1: entrada

```
Escopo: cada valor que vem do cliente (corpo, endereço, parâmetro, cabeçalho). Siga cada um até
onde ele é usado. Ele passa por uma lista do que é aceito (formato, tamanho, opções)? O que vem
do cliente vai direto para o banco?
```

## Rodada 2: endpoints

```
Escopo: as rotas do app, as novas e as antigas. Para cada uma: quem chama, o que ela exige antes
de agir, quantas linhas ou quantos pedidos ela aceita. Há rota que ninguém chama?
```

## Rodada 3: autenticação e autorização

```
Escopo: quem é a pessoa e o que ela pode. Rota por rota: exige login? Confere o papel (cliente,
admin) e o plano? Confere se o objeto pedido é da pessoa? Estar logado não basta.
```

## Rodada 4: banco

```
Escopo: cada consulta ao banco. Como ela é montada (valor por "?" ou colado no texto)? De onde
vem cada parte? Quantas linhas ela pode devolver? Há escrita que o cliente consegue disparar?
```

## Rodada 5: regra de negócio

```
Escopo: a regra de negócio. Traduza o código do PR em regras, em português, como se fosse
escrever o documento da loja. Depois compare, item por item, com o arquivo regras-da-loja.md.
Aponte toda diferença, inclusive de dia, hora, fuso horário, quem pode e o que soma com o quê.
```

## Depois de cada rodada

- O que o revisor aponta é hipótese. Mostre com um pedido (`python3 pedir.py ...`) ou com um teste antes de chamar de achado.
- "Nada neste escopo" não prova que o escopo está limpo. Anote o que ele disse que leu.
- A resposta muda de uma rodada para outra, e de um modelo para outro. Anote a ferramenta, o modelo e a data.
