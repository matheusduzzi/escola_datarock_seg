"""Restaura um backup numa pasta separada e mostra se ele volta a loja inteira.

    python3 restaurar.py backups/loja-copia.db --comparar loja/loja.db
    python3 restaurar.py backups/loja-2026-11-09-0200.db --comparar loja/loja.db
    python3 restaurar.py backups/loja-2026-11-09-0200.db --comparar loja/loja.db --devolver AUR-1323,AUR-1331

Nunca grava por cima do banco da loja. Copia o backup para restaurado/loja.db, abre a
cópia e checa: o arquivo é o mesmo do manifesto (quando tem manifesto), o SQLite diz que
ele está íntegro, a contagem bate com o manifesto e, com --comparar, quais pedidos da
loja faltam no backup e quais a loja perdeu desde o backup.

Com --devolver, copia esses pedidos da cópia restaurada de volta para o banco do
--comparar. Só devolve pedido que o backup tem e a loja não.

Sai com 0 quando o backup volta a loja inteira e com 1 quando falta alguma coisa.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

PASTA_RESTAURADO = Path('restaurado')
CAMPOS = 'codigo, cliente, produto, valor_centavos, criado_em'


def pedidos(caminho):
    con = sqlite3.connect(caminho)
    try:
        return {linha[0]: linha for linha in con.execute(f'select {CAMPOS} from pedidos order by codigo')}
    finally:
        con.close()


def lista(codigos):
    return ', '.join(sorted(codigos))


def main():
    p = argparse.ArgumentParser(description='Restaura um backup e mostra o que ele traz.')
    p.add_argument('backup')
    p.add_argument('--comparar', help='banco da loja, só para leitura (menos com --devolver)')
    p.add_argument('--devolver', help='códigos separados por vírgula, devolvidos ao banco do --comparar')
    a = p.parse_args()
    backup = Path(a.backup)
    if not backup.exists():
        print(f'Não achei {a.backup}.')
        return 2
    if a.devolver and not a.comparar:
        print('O --devolver precisa do --comparar com o banco da loja.')
        return 2
    problemas = []
    print(f'Backup: {backup.as_posix()}')
    manifesto = None
    arquivo_manifesto = backup.with_suffix('.json')
    if arquivo_manifesto.exists():
        manifesto = json.loads(arquivo_manifesto.read_text(encoding='utf-8'))
        print(f'Manifesto: {manifesto["pedidos"]} pedidos, último {manifesto["ultimo_pedido"]}, feito em {manifesto["feito_em"]}')
        igual = hashlib.sha256(backup.read_bytes()).hexdigest() == manifesto['sha256']
        print('Arquivo igual ao do manifesto:', 'sim' if igual else 'NÃO')
        if not igual:
            problemas.append('o arquivo mudou depois do backup')
    else:
        print('Manifesto: não tem. Não dá para saber o que esse backup deveria trazer.')

    PASTA_RESTAURADO.mkdir(exist_ok=True)
    restaurado = PASTA_RESTAURADO / 'loja.db'
    for sufixo in ('', '-wal', '-shm', '-journal'):
        Path(str(restaurado) + sufixo).unlink(missing_ok=True)
    shutil.copyfile(backup, restaurado)
    print(f'Restaurei em {restaurado.as_posix()}. O banco da loja não foi tocado.')

    con = sqlite3.connect(restaurado)
    try:
        integridade = con.execute('pragma integrity_check').fetchone()[0]
    except sqlite3.DatabaseError as erro:
        integridade = f'o SQLite não abre o arquivo ({erro})'
    finally:
        con.close()
    print('Integridade:', integridade)
    if integridade != 'ok':
        problemas.append('o arquivo não está íntegro')
        print('RESULTADO: esse backup não volta a loja.')
        return 1

    no_backup = pedidos(restaurado)
    ultimo = max(no_backup) if no_backup else 'nenhum'
    texto = f'No backup restaurado: {len(no_backup)} pedidos, último {ultimo}'
    if manifesto:
        if len(no_backup) == manifesto['pedidos'] and ultimo == manifesto['ultimo_pedido']:
            texto += ', igual ao manifesto'
        else:
            texto += ', DIFERENTE do manifesto'
            problemas.append('a contagem não bate com o manifesto')
    print(texto)

    if a.comparar:
        na_loja = pedidos(a.comparar)
        print(f'Na loja ({a.comparar}): {len(na_loja)} pedidos')
        corte = datetime.datetime.fromisoformat(manifesto['feito_em']) if manifesto else None
        faltam = {c for c in na_loja if c not in no_backup
                  and (corte is None or datetime.datetime.fromisoformat(na_loja[c][4]) <= corte)}
        novos = {c for c in na_loja if c not in no_backup} - faltam
        perdidos = {c for c in no_backup if c not in na_loja}
        if faltam:
            problemas.append('faltam pedidos no backup')
            print(f'FALTAM NO BACKUP {len(faltam)}: {lista(faltam)}')
        if novos:
            print(f'Novos depois do backup {len(novos)}: {lista(novos)}')
        if perdidos:
            print(f'A LOJA PERDEU {len(perdidos)} desde o backup: {lista(perdidos)}')
        if not (faltam or novos or perdidos):
            print('Backup e loja têm os mesmos pedidos.')
        if a.devolver:
            pedidos_devolver = [c.strip() for c in a.devolver.split(',') if c.strip()]
            fora = [c for c in pedidos_devolver if c not in perdidos]
            if fora:
                print(f'Não devolvi nada: {lista(fora)} não está entre os que a loja perdeu.')
                return 2
            con = sqlite3.connect(a.comparar)
            with con:
                con.executemany(f'insert into pedidos ({CAMPOS}) values (?, ?, ?, ?, ?)',
                                [no_backup[c] for c in pedidos_devolver])
            con.close()
            print(f'Devolvi {len(pedidos_devolver)} para {a.comparar}: {lista(pedidos_devolver)}')

    if problemas:
        print('RESULTADO: esse backup não volta a loja inteira (' + '; '.join(problemas) + ').')
        return 1
    print('RESULTADO: o backup volta a loja inteira.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
