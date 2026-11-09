# Infra própria, backup e trilha de auditoria

Os comandos partem dessa pasta. No Windows, troque `python3` por `py` e rode os comandos com `sh` pelo Git Bash, que vem com o git.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `servidor/Dockerfile` e `servidor/sshd_config` | o servidor da loja num contêiner, do jeito que veio do provedor: root com senha |
| `checar_servidor.py` | diz como se entra no servidor: pela configuração (`config`) e batendo na porta (`acesso`) |
| `loja/preparar.py` | monta o banco da loja como ele está às 2h, com a loja aberta |
| `backup_antigo.sh` | o backup que estava no cron: copia o arquivo e diz "ok" |
| `backup.py` | o backup pelo próprio SQLite, com manifesto |
| `restaurar.py` | restaura um backup numa pasta separada e mostra se ele volta a loja inteira |
| `agente_noturno.py` | o agente da noite, de roteiro: sem modelo de IA, faz sempre a mesma tarefa |
| `trilha.py` | lê e verifica a trilha do que o agente fez |
| `relogio.py` | a hora que os programas anotam |
| `exercicio/` | os arquivos do exercício |
| `minhas-respostas.md` | o modelo para as suas respostas |

O servidor precisa do Docker. As partes de backup e trilha precisam só do Python.

## Passo 1: o servidor

```
docker build -t aurora-servidor servidor
docker run -d --name servidor -p 127.0.0.1:2222:22 aurora-servidor
docker exec servidor sshd -T | python3 checar_servidor.py config
ssh-keygen -t ed25519 -C aurora-curso -f chave-aurora
python3 checar_servidor.py acesso --porta 2222 --chave chave-aurora
```

O `-p 127.0.0.1:2222:22` publica a porta só no seu computador. Sem o `127.0.0.1`, o Docker publica para a rede inteira.

O `ssh-keygen` pede uma frase para proteger a chave. Use uma: ela vale para o arquivo `chave-aurora`, que é a parte privada e nunca sai do seu computador. A parte pública é a `chave-aurora.pub`.

Instale a chave pública no servidor. O comando pede a senha do usuário `aurora` uma vez: `aurora-teste`.

```
ssh-copy-id -i chave-aurora.pub -p 2222 aurora@127.0.0.1
python3 checar_servidor.py acesso --porta 2222 --chave chave-aurora
```

Sem o `ssh-copy-id` (no Windows, por exemplo):

```
docker cp chave-aurora.pub servidor:/tmp/chave.pub
docker exec servidor sh -c "mkdir -p /home/aurora/.ssh && cat /tmp/chave.pub >> /home/aurora/.ssh/authorized_keys && chown -R aurora:aurora /home/aurora/.ssh && chmod 700 /home/aurora/.ssh && chmod 600 /home/aurora/.ssh/authorized_keys"
```

Com a chave entrando, mude as duas linhas em `servidor/sshd_config` (`PermitRootLogin no` e `PasswordAuthentication no`), mande o arquivo para o servidor, teste e reinicie:

```
docker cp servidor/sshd_config servidor:/etc/ssh/sshd_config
docker exec servidor sshd -t
docker restart servidor
docker exec servidor sshd -T | python3 checar_servidor.py config
python3 checar_servidor.py acesso --porta 2222 --chave chave-aurora
```

O `sshd -t` não mostra nada quando a configuração está certa. Se ele mostrar um erro, corrija antes do `docker restart`.

Para entrar no servidor: `ssh -i chave-aurora -p 2222 aurora@127.0.0.1`. O `checar_servidor.py` não confere a impressão digital do servidor, porque ela muda a cada `docker build`. Num servidor de verdade, olhe se ela bate na primeira conexão.

## Passo 2: o backup

```
python3 loja/preparar.py
sh backup_antigo.sh
python3 restaurar.py backups/loja-copia.db --comparar loja/loja.db
python3 backup.py
python3 restaurar.py backups/loja-AAAA-MM-DD-HHMM.db --comparar loja/loja.db
```

Rode o `backup_antigo.sh` logo depois do `preparar.py`, antes de qualquer outro comando: é assim que o cron encontra a loja às 2h. No último comando, use o nome que o `backup.py` mostrou.

O `restaurar.py` nunca grava por cima do banco da loja. Ele restaura em `restaurado/loja.db`.

## Passo 3: a trilha

```
python3 agente_noturno.py
python3 trilha.py ver
python3 trilha.py verificar
python3 trilha.py ancora
python3 restaurar.py backups/loja-AAAA-MM-DD-HHMM.db --comparar loja/loja.db
```

Copie a linha que o `ancora` mostra para um lugar que o agente não alcança: uma mensagem para você mesmo, por exemplo. Depois, para verificar com ela:

```
python3 trilha.py verificar --ancora "6 5609..."
```

Para devolver os pedidos que a loja perdeu, use os códigos que o `restaurar.py` listou:

```
python3 restaurar.py backups/loja-AAAA-MM-DD-HHMM.db --comparar loja/loja.db --devolver AUR-1323,AUR-1331,AUR-1339
```

## Começar de novo

`python3 loja/preparar.py` refaz o banco. Para a trilha e os backups, apague as pastas `trilha/`, `backups/`, `restaurado/` e `rascunhos/`. Para o servidor: `docker rm -f servidor`.

## O exercício

O enunciado está na aula. Os arquivos:

- `exercicio/servidor-novo/`: a configuração do SSH do servidor novo, com a pasta `sshd_config.d`;
- `exercicio/terca/`: a trilha da terça, a âncora que saiu do servidor, o backup da madrugada de quarta e a loja na quarta de manhã.

Copie `exercicio/terca/loja-quarta.db` para a pasta da aula antes de devolver pedidos, para manter o original.

## Ajuda

Deixe um comentário na aula com o seu objetivo, o comando que você rodou, a saída e o que já tentou. Nunca cole a chave privada, a senha ou a trilha com dado de cliente no comentário.
