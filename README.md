# Kit de Segurança no trabalho com IA

Comece pela pasta `00-apresentacao`. Ela tem a ficha inicial, as tarefas de preparação e um arquivo para as suas respostas.

1. Instale o Python (3.9 ou mais novo) e o git, se ainda não tiver.
2. Abra um terminal na pasta `00-apresentacao` e rode `python3 checar_ambiente.py`.
3. Preencha a [ficha inicial](00-apresentacao/ficha-inicial.md).
4. Faça [as tarefas](00-apresentacao/diagnostico.md) numa cópia de [minhas-respostas.md](00-apresentacao/minhas-respostas.md).

No Windows, troque `python3` por `py` nos comandos.

## O que tem aqui

| Pasta | O que é |
|---|---|
| `00-apresentacao/` | ficha inicial, tarefas de preparação e os arquivos delas em `material/` |
| `loja-aurora/` | o app da Loja Aurora, com falhas de propósito, e o `sondar.py`, que diz quais continuam abertas |
| `mensagens/` | as 15 mensagens que chegam ao atendimento da loja numa manhã, usadas nas aulas 09, 10 e 11 |

Cada aula com arquivos ganha uma pasta com o número e o nome dela, como `03-segredos-fora-do-codigo/`. Os comandos do texto da aula partem dessa pasta. Os arquivos das outras aulas entram aqui conforme as aulas saem; não procure o que ainda não está listado.

## A Loja Aurora

É uma loja de luminárias e decoração que existe só no curso. O app roda no seu computador, em `http://127.0.0.1:8765`, e guarda tudo num arquivo SQLite dentro da própria pasta.

```
cd loja-aurora
python3 app.py              # abre a loja; Ctrl+C para parar
python3 sondar.py           # testa as falhas conhecidas
python3 -m unittest -v      # testa se a loja continua funcionando
python3 dados.py            # apaga e recria o banco com os dados do começo
```

O `sondar.py` sobe uma cópia da loja numa porta livre do seu computador, com um banco novo, faz as checagens e desliga. Ele sai com `1` enquanto alguma falha estiver aberta e com `0` quando todas fecharem. No começo do curso, todas aparecem como `ABERTA`: é assim mesmo.

As contas de teste da loja estão em `loja-aurora/dados.py`. Os nomes, e-mails e pedidos são inventados, e os e-mails usam o domínio `example`, que não entrega mensagem para ninguém. As chaves do `.env.exemplo` têm o formato `aurora_..._teste_` e não abrem conta nenhuma.

## A regra do curso

Todo ataque do curso acontece na Loja Aurora, no seu computador. Não teste nada disso em site, app ou sistema de outra pessoa ou empresa, nem "só para ver". O app escuta só em `127.0.0.1` e não deve ser publicado, nem copiado como base de um projeto real.

Quando uma aula pedir uma chave de verdade (de um provedor de IA, por exemplo), crie uma chave só para o curso, com teto de gasto e validade curta, e revogue no fim. Chave nunca vai para o código, para o chat nem para print.

## O que mais você vai usar

- **Agora:** Python 3.9 ou mais novo, git e um editor de texto.
- **Aula 08 em diante:** Docker, para rodar o agente num contêiner isolado.
- **Aulas 06 a 08:** um agente de código que você já usa, como o Claude Code ou o Codex. Os modos de permissão mudam rápido; as aulas citam a documentação com a data.
- **Aula 10:** o n8n é opcional. Quem não usa faz a mesma prática com um script.
- **Aulas 14 e 15:** o Supabase rodando no seu computador, pelo Docker. As aulas mostram a instalação.
- **Aula 18:** Node e npm.

## Licença e ajuda

Os textos, o app e os dados do kit foram feitos para a Escola Datarock. A licença de redistribuição do kit ainda vai ser definida.

Para pedir ajuda, deixe um comentário na aula com o seu objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole uma chave, senha ou dado pessoal no comentário.

## Aulas com arquivos neste kit

| Pasta | Aula |
|---|---|
| [00-apresentacao/](00-apresentacao/) | Apresentação |
| [01-o-novo-cenario-a-ia-acelera-o-ataque-e-a-defesa/](01-o-novo-cenario-a-ia-acelera-o-ataque-e-a-defesa/) | O novo cenário: a IA acelera o ataque e a defesa |
| [02-modelo-de-ameaca-em-uma-pagina/](02-modelo-de-ameaca-em-uma-pagina/) | Modelo de ameaça em uma página |
| [03-segredos-fora-do-codigo-do-chat-e-da-tela/](03-segredos-fora-do-codigo-do-chat-e-da-tela/) | Segredos fora do código, do chat e da tela |
| [05-cofre-de-senhas-e-contas-proprias-para-o-agente/](05-cofre-de-senhas-e-contas-proprias-para-o-agente/) | Cofre de senhas e contas próprias para o agente |
| [06-modos-de-aprovacao-perguntar-aprovar-por-mim-e/](06-modos-de-aprovacao-perguntar-aprovar-por-mim-e/) | Modos de aprovação: perguntar, aprovar por mim e pular permissões |
| [07-o-contrato-de-acesso-do-agente/](07-o-contrato-de-acesso-do-agente/) | O contrato de acesso do agente |
| [08-sandbox-de-verdade/](08-sandbox-de-verdade/) | Sandbox de verdade |
| [09-prompt-injection-tudo-o-que-entra-e-dado/](09-prompt-injection-tudo-o-que-entra-e-dado/) | Prompt injection: tudo o que entra é dado |
| [10-ferramentas-restritas-no-lugar-de-ferramentas/](10-ferramentas-restritas-no-lugar-de-ferramentas/) | Ferramentas restritas no lugar de ferramentas cruas |
| [11-skills-plugins-mcp-e-bots-de-terceiros/](11-skills-plugins-mcp-e-bots-de-terceiros/) | Skills, plugins, MCP e bots de terceiros |
| [12-autenticacao-pronta-e-regra-no-servidor/](12-autenticacao-pronta-e-regra-no-servidor/) | Autenticação pronta e regra no servidor |
| [13-rls-que-protege-de-verdade-no-supabase/](13-rls-que-protege-de-verdade-no-supabase/) | RLS que protege de verdade no Supabase |
| [16-dado-pessoal-e-confidencial-na-ia/](16-dado-pessoal-e-confidencial-na-ia/) | Dado pessoal e confidencial na IA |
| [17-lgpd-no-dia-a-dia-de-quem-usa-ia/](17-lgpd-no-dia-a-dia-de-quem-usa-ia/) | LGPD no dia a dia de quem usa IA |
| [18-engenharia-social-a-maquina-de-quem-trabalha-e-a/](18-engenharia-social-a-maquina-de-quem-trabalha-e-a/) | Engenharia social: a máquina de quem trabalha é a porta |
| [19-golpes-contra-voce-e-seus-clientes/](19-golpes-contra-voce-e-seus-clientes/) | Golpes contra você e seus clientes |
| [20-infra-propria-backup-e-trilha-de-auditoria/](20-infra-propria-backup-e-trilha-de-auditoria/) | Infra própria, backup e trilha de auditoria |
| [21-projeto-final-auditoria-do-proprio-setup-e-plano/](21-projeto-final-auditoria-do-proprio-setup-e-plano/) | Projeto final: auditoria do próprio setup e plano de incidente |
| [22-guardrails-de-entrada-e-saida-o-que-barram-e-o/](22-guardrails-de-entrada-e-saida-o-que-barram-e-o/) | Guardrails de entrada e saída: o que barram e o que deixam passar |
| [23-o-que-pula-o-rls-views-funcoes-metadados-chave/](23-o-que-pula-o-rls-views-funcoes-metadados-chave/) | O que pula o RLS: views, funções, metadados, chave secreta e storage |
| [24-quem-ve-e-quem-muda-o-que-idor-e-mass-assignment/](24-quem-ve-e-quem-muda-o-que-idor-e-mass-assignment/) | Quem vê e quem muda o quê: IDOR e mass assignment |
| [25-dependencias-o-que-o-agente-instala/](25-dependencias-o-que-o-agente-instala/) | Dependências: o que o agente instala |
