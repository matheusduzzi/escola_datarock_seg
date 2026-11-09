# Por onde começar

São seis tarefas curtas. Elas mostram o que você já reconhece e quais aulas vão pedir mais de você. Não tem nota. Escreva as respostas numa cópia de [minhas-respostas.md](minhas-respostas.md), em tópicos se preferir.

Faça sem pedir a resposta pronta para uma IA. A ideia é ver como você pensa hoje. Os arquivos das tarefas estão na pasta `material/`.

## Tarefa 1: o seu computador

Dentro dessa pasta, rode:

```
python3 checar_ambiente.py
```

Cole a saída na resposta. Para começar, precisa sair `Tudo certo para começar.` Docker, Node e npm podem aparecer como `aviso`: eles só entram nas aulas 08 e 18.

Se o comando não rodar, o `README.md` do kit mostra como instalar o Python e o git.

## Tarefa 2: onde a chave foi parar

A Carla, do financeiro, mandou uma chave para o Diego, que cuida do site. Leia os três arquivos:

- `material/conversa-equipe.txt`
- `material/config-do-site.js`
- `material/gitignore-do-projeto.txt`

Responda:

1. Em que lugares a chave secreta do gateway aparece?
2. Das quatro chaves do `config-do-site.js`, quais podem ficar no navegador e quais não podem?
3. O que o `.gitignore` deixa de proteger?
4. Qual é a primeira coisa a fazer com a chave secreta, antes de apagar qualquer arquivo?

## Tarefa 3: mensagem ou ordem

Um agente de IA lê o atendimento da loja e pode responder, mudar pedido e aprovar estorno. Leia `material/mensagens-curtas.txt`.

Para cada uma das cinco mensagens, diga se é um pedido normal de cliente ou se tem uma ordem escondida para a IA. Nas que têm ordem escondida, diga o que o agente faria se obedecesse.

## Tarefa 4: o login que a IA escreveu

Abra `material/login_trecho.py`. Você não precisa saber programar para esta tarefa: leia devagar, linha por linha.

1. O que vem do cliente (o e-mail e a senha) entra direto na consulta ao banco? Em que linha?
2. As duas mensagens de erro contam alguma coisa para quem está tentando adivinhar contas?
3. Como a senha está guardada no banco, pelo que o código mostra?

Se programar não é a sua praia, responda só a 1 e a 2.

## Tarefa 5: a loja do curso

O kit traz a Loja Aurora, uma loja de luminárias e decoração que roda só no seu computador. Ela vem com falhas de propósito: no curso, você acha e corrige cada uma.

Na pasta `loja-aurora/` do kit, rode:

```
python3 sondar.py
```

1. Quantas checagens aparecem como `ABERTA`?
2. Escolha a que você corrigiria primeiro e diga por quê, em uma ou duas frases.

## Tarefa 6: o SMS urgente

Leia `material/mensagem-urgente.txt`.

1. O que você faria nos próximos cinco minutos?
2. A conta tem verificação em duas etapas por SMS. Isso protege a loja nesse caso?
