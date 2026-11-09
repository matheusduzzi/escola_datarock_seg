#!/bin/sh
# O backup que o Diego pôs no cron do servidor, todo dia às 2h:
#   0 2 * * * cd /srv/aurora && sh backup_antigo.sh
# Copia o arquivo do banco e diz que deu certo. Ninguém nunca restaurou.
mkdir -p backups
cp loja/loja.db backups/loja-copia.db
echo "backup ok: backups/loja-copia.db"
