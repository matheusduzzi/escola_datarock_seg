"""Mostra o que já está pronto no seu computador para o curso.

    python3 checar_ambiente.py

Sai com 0 quando o mínimo para começar está pronto (Python 3.9+ e git) e com 1 quando falta
algo desse mínimo. Docker e Node aparecem como aviso: só entram mais para a frente.
Não lê nem mostra nenhuma chave.
"""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def versao(comando):
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=15)
        return (saida.stdout or saida.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return ''


def main():
    faltando = 0
    print('Mínimo para começar')
    ok = sys.version_info >= (3, 9)
    faltando += not ok
    print(f'  {"ok" if ok else "FALTA":7}Python {sys.version.split()[0]} (precisa 3.9 ou mais novo)')
    git = shutil.which('git')
    faltando += not git
    print(f'  {"ok" if git else "FALTA":7}{versao(["git", "--version"]) if git else "git não encontrado"}')
    print(f'  ok     SQLite {sqlite3.sqlite_version} (vem com o Python)')
    ignorados = (KIT / '.gitignore').read_text(encoding='utf-8').split() if (KIT / '.gitignore').exists() else []
    tem_env = '.env' in ignorados
    faltando += not tem_env
    print(f'  {"ok" if tem_env else "FALTA":7}.env listado no .gitignore do kit')

    print('\nPara depois (aviso, não impede começar)')
    for nome, comando, quando in [
        ('docker', ['docker', '--version'], 'contêiner isolado, a partir da aula 08'),
        ('node', ['node', '--version'], 'dependências de JavaScript, na aula 18'),
        ('npm', ['npm', '--version'], 'auditoria de pacotes, na aula 18'),
    ]:
        achou = shutil.which(nome)
        print(f'  {"ok" if achou else "aviso":7}{nome} {versao(comando) if achou else "não encontrado"}: {quando}')

    print('\nTudo certo para começar.' if not faltando else f'\nFalta {faltando} item do mínimo. Veja o README do kit.')
    return 0 if not faltando else 1


if __name__ == '__main__':
    sys.exit(main())
