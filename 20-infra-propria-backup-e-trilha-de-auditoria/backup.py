"""Faz o backup do banco da loja pelo próprio SQLite e anota o que ele tem.

    python3 backup.py
    python3 backup.py --banco loja/loja.db --destino backups

Usa a API de backup do SQLite, que copia o banco inteiro mesmo com a loja aberta,
incluindo o que ainda está no arquivo -wal. Grava ao lado um manifesto (.json) com a
hora, o sha256 do arquivo, quantos pedidos ele tem e qual é o último. É o manifesto que
o restaurar.py usa para saber o que o backup deveria trazer.

Num servidor de verdade, o backup não fica só no servidor: uma cópia vai para um lugar
que nem o servidor nem o agente conseguem apagar.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from relogio import agora

PASTA = Path(__file__).resolve().parent


def resumo(caminho):
    con = sqlite3.connect(caminho)
    try:
        n, ultimo = con.execute('select count(*), max(codigo) from pedidos').fetchone()
        return n, ultimo
    finally:
        con.close()


def main():
    p = argparse.ArgumentParser(description='Backup do banco da loja com manifesto.')
    p.add_argument('--banco', default='loja/loja.db')
    p.add_argument('--destino', default='backups')
    a = p.parse_args()
    banco, destino = Path(a.banco), Path(a.destino)
    if not banco.exists():
        print(f'Não achei {a.banco}. Rode antes: python3 loja/preparar.py')
        return 2
    destino.mkdir(parents=True, exist_ok=True)
    hora = agora()
    alvo = destino / f'loja-{hora:%Y-%m-%d-%H%M}.db'
    alvo.unlink(missing_ok=True)
    origem = sqlite3.connect(banco)
    copia = sqlite3.connect(alvo)
    try:
        origem.backup(copia)
        # O backup sai num arquivo só, sem -wal ao lado: é ele que vai para fora do servidor.
        copia.execute('pragma journal_mode=delete').fetchall()
    finally:
        copia.close()
        origem.close()
    for sobra in ('-wal', '-shm'):   # o SQLite de alguns sistemas deixa esses arquivos vazios ao lado
        Path(str(alvo) + sobra).unlink(missing_ok=True)
    n, ultimo = resumo(alvo)
    sha = hashlib.sha256(alvo.read_bytes()).hexdigest()
    manifesto = {'arquivo': alvo.name, 'feito_em': hora.isoformat(), 'sha256': sha,
                 'pedidos': n, 'ultimo_pedido': ultimo}
    nome_manifesto = alvo.with_suffix('.json')
    nome_manifesto.write_text(json.dumps(manifesto, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Backup: {alvo.as_posix()}')
    print(f'Pedidos: {n}, último {ultimo}')
    print(f'Manifesto: {nome_manifesto.as_posix()} (sha256 {sha[:12]}…)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
