"""Monta repo-aurora/: o repositório git da Loja Aurora, com a main e o PR do Diego.

    python3 montar.py            # cria repo-aurora/ (se já existir, não mexe)
    python3 montar.py --de-novo  # apaga repo-aurora/ e cria de novo, do começo

A main tem a loja como ficou depois da aula «Webhook, limite de requisições e consulta
parametrizada» (os arquivos da pasta loja/). A branch cupom-sexta é o PR do Diego, com três
commits feitos pelo agente dele (os arquivos da pasta pr-cupom-sexta/). Os commits saem com
nome e data fixos e só levam os arquivos da loja: o .DS_Store do Finder, o Thumbs.db do Windows
e outros arquivos ocultos ficam de fora. Assim os ids dos commits são os mesmos em qualquer
computador, enquanto os arquivos de loja/ e pr-cupom-sexta/ não forem editados.
"""
import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI / 'repo-aurora'
LOJA = AQUI / 'loja'
PR = AQUI / 'pr-cupom-sexta'

# A chave que o agente colou no código no segundo commit. É da loja do curso e não abre nada.
CHAVE = 'aurora_sk_live_Rq8Vt3Wm6Yp1Kx4Nz9Hd'
TRECHO_CHAVE = (
    "\n# Chave do gateway para testar a Sexta Aurora com pagamento de verdade. Tirar antes do merge.\n"
    f"PAGAMENTO_CHAVE_SECRETA = '{CHAVE}'\n"
)

RENATA = ('Renata Alves', 'renata@aurora.example')
DIEGO = ('Diego (agente)', 'diego@aurora.example')


def git(*args, quem=RENATA, quando='2026-11-20T09:00:00-03:00'):
    env = dict(os.environ, GIT_AUTHOR_NAME=quem[0], GIT_AUTHOR_EMAIL=quem[1], GIT_COMMITTER_NAME=quem[0],
               GIT_COMMITTER_EMAIL=quem[1], GIT_AUTHOR_DATE=quando, GIT_COMMITTER_DATE=quando)
    r = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'commit.gpgsign=false', '-c', 'init.defaultBranch=main', *args],
                       cwd=REPO, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'git {" ".join(args)} falhou: {r.stderr.strip()}')
    return r.stdout


# Ocultos que fazem parte da loja. Qualquer outro arquivo que começa com ponto fica fora do commit.
OCULTOS_DA_LOJA = {'.env.exemplo', '.gitignore'}
# O que o sistema cria sozinho na pasta (Finder, Windows Explorer) e mudaria os ids dos commits.
LIXO_DO_SISTEMA = {'Thumbs.db', 'desktop.ini', 'Icon\r'}


def entra_no_commit(relativo):
    if '__pycache__' in relativo.parts or relativo.suffix in ('.db', '.pyc'):
        return False
    if any(parte.startswith('.') for parte in relativo.parts[:-1]):
        return False
    nome = relativo.name
    if nome.startswith('.') and nome not in OCULTOS_DA_LOJA:
        return False
    return nome not in LIXO_DO_SISTEMA


def copiar(origem, nomes=None):
    for arquivo in sorted(Path(origem).rglob('*')):
        relativo = arquivo.relative_to(origem)
        if arquivo.is_dir() or not entra_no_commit(relativo):
            continue
        if nomes is not None and relativo.as_posix() not in nomes:
            continue
        destino = REPO / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(arquivo.read_bytes())


def apagar(pasta):
    def liberar(funcao, caminho, _):   # o git marca alguns arquivos como só leitura (Windows)
        os.chmod(caminho, stat.S_IWRITE)
        funcao(caminho)
    shutil.rmtree(pasta, onerror=liberar)


def montar():
    REPO.mkdir()
    git('init', '-q')
    git('symbolic-ref', 'HEAD', 'refs/heads/main')
    copiar(LOJA)
    git('add', '-A')
    git('commit', '-q', '-m', 'Loja Aurora: versão que vai para a campanha de fim de ano')

    git('checkout', '-q', '-b', 'cupom-sexta')
    copiar(PR)
    git('add', '-A')
    git('commit', '-q', '-m', 'Sexta Aurora: 10% de desconto às sextas e relatório de vendas do dia',
        quem=DIEGO, quando='2026-11-23T10:12:00-03:00')

    app = REPO / 'app.py'
    original = app.read_text(encoding='utf-8')
    marca = "HOST = '127.0.0.1'\n"
    assert original.count(marca) == 1
    app.write_text(original.replace(marca, marca + TRECHO_CHAVE), encoding='utf-8')
    git('commit', '-q', '-am', 'Testa a Sexta Aurora com o gateway de verdade',
        quem=DIEGO, quando='2026-11-23T11:40:00-03:00')

    app.write_text(original, encoding='utf-8')
    git('commit', '-q', '-am', 'Tira a chave do código: ela vai pelo .env',
        quem=DIEGO, quando='2026-11-23T11:58:00-03:00')


def main():
    parser = argparse.ArgumentParser(description='Monta o repositório git da Loja Aurora com o PR do Diego.')
    parser.add_argument('--de-novo', action='store_true', help='apaga repo-aurora/ e cria de novo')
    args = parser.parse_args()
    if REPO.exists():
        if not args.de_novo:
            print(f'{REPO.name}/ já existe. Para começar do zero: python3 montar.py --de-novo')
            return 0
        apagar(REPO)
    montar()
    print(f'{REPO.name}/ criado. Branches:')
    print(git('branch', '-v').rstrip())
    print('\nCommits do PR (cupom-sexta contra main):')
    print(git('log', '--reverse', '--format=  %h %ad %an  %s', '--date=format:%d/%m %H:%M', 'main..cupom-sexta').rstrip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
