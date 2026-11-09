"""Monta o banco da Loja Aurora como ele está às 2h da manhã, com a loja no ar.

    python3 loja/preparar.py

Apaga e recria loja/loja.db com 40 pedidos. Os 36 primeiros já estão no arquivo
loja.db. Os 4 da noite (AUR-1337 a AUR-1340) ainda estão no loja.db-wal: o SQLite
anota a mudança nesse arquivo ao lado e só passa para o loja.db no próximo checkpoint.
O programa sai sem fechar o banco, como a loja que continua aberta, e o loja.db-wal fica.

Rode de novo para voltar ao começo da aula.
"""
import os
import sqlite3
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
BANCO = PASTA / 'loja.db'

CLIENTES = ['Bia Santos', 'Caio Lima', 'Duda Rocha', 'Elis Moura', 'Fábio Nunes',
            'Gabi Prado', 'Hugo Reis', 'Íris Campos', 'Júlia Teles', 'Léo Barros']
PRODUTOS = [('Luminária de mesa Aurora', 24990), ('Pendente de vidro Bruma', 31950),
            ('Fita de LED quente 5 m', 8990), ('Lâmpada filamento 4 W', 2490),
            ('Vela aromática Alecrim', 6990), ('Vaso de cerâmica Duna', 12900),
            ('Manta de algodão Serra', 15990), ('Espelho redondo Lago', 27900)]
# Três clientes compraram de novo o mesmo produto no mesmo dia. São pedidos de verdade.
REPETIDOS = {1323: 1322, 1331: 1330, 1339: 1338}
# Os 4 pedidos da noite de 08/11.
NOITE = {1337: '19:12', 1338: '19:40', 1339: '20:55', 1340: '21:30'}


def pedidos():
    for n in range(1301, 1341):
        base = REPETIDOS.get(n, n)
        i = base - 1301
        cliente = CLIENTES[(i * 3) % len(CLIENTES)]
        produto, preco = PRODUTOS[(i * 5) % len(PRODUTOS)]
        dia = 2 + (i * 7) // 40            # de 02/11 a 08/11
        hora = 9 + (base * 7) % 10 + (2 if n in REPETIDOS else 0)
        minuto = (n * 13) % 60
        hhmm = NOITE.get(n, f'{hora:02d}:{minuto:02d}')
        yield (f'AUR-{n}', cliente, produto, preco, f'2026-11-{dia:02d}T{hhmm}:00-03:00')


def montar():
    for sufixo in ('', '-wal', '-shm'):
        Path(str(BANCO) + sufixo).unlink(missing_ok=True)
    con = sqlite3.connect(BANCO)
    con.execute('pragma journal_mode=wal').fetchall()
    con.execute('create table pedidos (id integer primary key, codigo text unique, cliente text,'
                ' produto text, valor_centavos integer, criado_em text)')
    todos = list(pedidos())
    sql = 'insert into pedidos (codigo, cliente, produto, valor_centavos, criado_em) values (?, ?, ?, ?, ?)'
    con.executemany(sql, todos[:36])
    con.commit()
    con.execute('pragma wal_checkpoint(truncate)').fetchall()   # até aqui, tudo no loja.db
    con.executemany(sql, todos[36:])                  # os pedidos da noite ficam no loja.db-wal
    con.commit()
    print(f'Loja montada em loja/loja.db: {len(todos)} pedidos, os 4 da noite ainda no loja.db-wal.')
    return con


if __name__ == '__main__':
    aberta = montar()   # a conexão fica aberta até o fim, como a da loja
    sys.stdout.flush()
    os._exit(0)   # sai sem fechar o banco: é assim que ele está com a loja aberta
