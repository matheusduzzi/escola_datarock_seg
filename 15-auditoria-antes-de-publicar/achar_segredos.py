"""Procura chaves numa pasta ou no histórico do git, sem mostrar a chave inteira.

    python3 achar_segredos.py PASTA               # os arquivos que estão na pasta agora
    python3 achar_segredos.py PASTA --historico   # todos os commits, de todas as branches

Mostra só o começo (o prefixo, que diz o tipo) e os 4 últimos caracteres de cada chave.
Sai com 1 quando acha alguma chave secreta e com 0 quando não acha nenhuma.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# (tipo, de onde é, padrão). O prefixo diz se a chave pode ir ao navegador.
PADROES = [
    ('secreta', 'gateway de pagamento', r'aurora_sk_(?:live|teste)_[A-Za-z0-9]{8,}'),
    ('secreta', 'webhook do gateway', r'aurora_whsec_(?:live|teste)_[A-Za-z0-9]{8,}'),
    ('secreta', 'provedor de IA', r'aurora_llm_sk_[A-Za-z0-9]{8,}'),
    ('pública', 'gateway de pagamento', r'aurora_pk_(?:live|teste)_[A-Za-z0-9]{8,}'),
    ('pública', 'mapa', r'aurora_mapa_pub_[A-Za-z0-9]{8,}'),
    # Formatos reais, para usar no seu projeto.
    ('secreta', 'Stripe', r'\b[sr]k_live_[A-Za-z0-9]{10,}'),
    ('secreta', 'GitHub', r'\bgh[pousr]_[A-Za-z0-9]{30,}'),
    ('secreta', 'Supabase', r'\bsb_secret_[A-Za-z0-9_-]{10,}'),
    ('pública', 'Stripe', r'\bpk_live_[A-Za-z0-9]{10,}'),
    ('pública', 'Supabase', r'\bsb_publishable_[A-Za-z0-9_-]{10,}'),
]
REGEX = [(t, o, re.compile(p)) for t, o, p in PADROES]
UNIAO = '|'.join('(' + p.replace('(?:', '(').replace(r'\b', '') + ')' for _, _, p in PADROES)


def mascarar(chave):
    prefixo = re.match(r'[a-z]+_(?:[a-z]+_)*', chave)
    return (prefixo.group(0) if prefixo else chave[:4]) + '…' + chave[-4:]


def achar(texto):
    for numero, linha in enumerate(texto.splitlines(), 1):
        for tipo, origem, regex in REGEX:
            for m in regex.finditer(linha):
                yield numero, tipo, origem, m.group(0)


def git(pasta, *args):
    r = subprocess.run(['git', *args], cwd=pasta, capture_output=True, text=True)
    return r.returncode, r.stdout


def na_pasta(pasta):
    achados = []
    for arquivo in sorted(p for p in Path(pasta).rglob('*') if p.is_file() and '.git' not in p.relative_to(pasta).parts):
        try:
            texto = arquivo.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        for numero, tipo, origem, chave in achar(texto):
            achados.append((tipo, origem, chave, f'{arquivo.relative_to(pasta).as_posix()}:{numero}', ''))
    return achados


def no_historico(pasta):
    # --reflog pega também commit de branch apagada: ele continua no seu git até ser limpo.
    codigo, saida = git(pasta, 'rev-list', '--all', '--reflog', '--reverse')
    if codigo != 0:
        sys.exit(f'{pasta} não é um repositório git.')
    _, atual = git(pasta, 'rev-parse', 'HEAD')
    primeiros = {}
    no_atual = set()
    for commit in saida.split():
        _, achou = git(pasta, 'grep', '-I', '-n', '-E', UNIAO, commit)
        for linha in achou.splitlines():
            _, arquivo, numero, texto = linha.split(':', 3)
            for _, tipo, origem, chave in achar(texto):
                chave_local = (chave, arquivo)
                primeiros.setdefault(chave_local, (tipo, origem, numero, commit))
                if commit == atual.strip():
                    no_atual.add(chave_local)
    achados = []
    for (chave, arquivo), (tipo, origem, numero, commit) in primeiros.items():
        _, info = git(pasta, 'log', '-1', '--date=short', '--format=%h %ad %an "%s"', commit)
        _, branches = git(pasta, 'branch', '--format=%(refname:short)', '--contains', commit)
        onde = 'ainda no commit atual' if (chave, arquivo) in no_atual else 'fora do commit atual'
        achados.append((tipo, origem, chave, f'{arquivo}:{numero}',
                        f'desde {info.strip()}, ' + (f'branch {", ".join(branches.split())}' if branches.split() else
                        'em nenhuma branch (apagada)') + f', {onde}'))
    return achados


def main():
    parser = argparse.ArgumentParser(description='Procura chaves numa pasta ou no histórico do git.')
    parser.add_argument('pasta', nargs='?', default='.')
    parser.add_argument('--historico', action='store_true', help='olha todos os commits de todas as branches')
    args = parser.parse_args()
    pasta = Path(args.pasta).resolve()
    achados = no_historico(pasta) if args.historico else na_pasta(pasta)
    onde = 'no histórico (todas as branches)' if args.historico else 'nos arquivos'
    print(f'Chaves {onde} de {pasta.name}:')
    for tipo, origem, chave, lugar, detalhe in achados:
        print(f'  {tipo:8} {origem:21} {mascarar(chave):22} {lugar:16} {detalhe}'.rstrip())
    secretas = sum(1 for a in achados if a[0] == 'secreta')
    print(f'{secretas} chave(s) secreta(s), {len(achados) - secretas} pública(s).' if achados else 'Nenhuma chave.')
    return 1 if secretas else 0


if __name__ == '__main__':
    sys.exit(main())
