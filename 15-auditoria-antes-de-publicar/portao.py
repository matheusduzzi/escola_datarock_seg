"""O portão do PR: as checagens que o CI roda antes de deixar um PR entrar na main.

    python3 portao.py repo-aurora                           # a branch atual contra a main
    python3 portao.py repo-aurora --branch cupom-sexta      # outra branch
    python3 portao.py repo-aurora --base main --branch minha-branch

Faz no seu computador, sem internet, o papel do workflow ci/portao.yml do GitHub Actions:

1. segredos: procura chave em cada commit do PR, linha por linha, como o gitleaks (git log -p);
2. dependências: confere o requirements.txt com os avisos da pasta avisos/, como o pip-audit;
3. código: roda as regras do sast.py no código da branch, como o Semgrep;
4. testes: roda python3 -m unittest numa cópia limpa da branch.

Sai com 1 quando alguma etapa falha (o PR fica barrado) e com 0 quando todas passam.
Os avisos da pasta avisos/ são uma cópia do banco público OSV (osv.dev) feita na data
escrita em cada arquivo. No CI de verdade, o pip-audit consulta o banco do dia.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import achar_segredos  # noqa: E402
import sast  # noqa: E402


def git(repo, *args, binario=False):
    r = subprocess.run(['git', '-c', 'core.quotepath=false', *args], cwd=repo, capture_output=True, text=not binario)
    if r.returncode != 0:
        erro = r.stderr if not binario else r.stderr.decode(errors='replace')
        raise SystemExit(f'git {" ".join(args)}: {erro.strip()}')
    return r.stdout


def commits_do_pr(repo, base, branch):
    return git(repo, 'rev-list', '--reverse', f'{base}..{branch}').split()


def extrair(repo, ref, destino):
    """Copia os arquivos da branch (o que está no git, sem .env nem banco) para uma pasta."""
    bruto = git(repo, 'archive', '--format=tar', ref, binario=True)
    with tarfile.open(fileobj=io.BytesIO(bruto)) as tar:
        try:
            tar.extractall(destino, filter='data')
        except TypeError:   # Python sem o parâmetro filter (antes de 3.9.17)
            tar.extractall(destino)
    return Path(destino)


# 1. Segredos -------------------------------------------------------------------------------

def segredos(repo, base, branch):
    """Cada chave acrescentada em algum commit do PR, mesmo que um commit depois tenha tirado."""
    achados = []
    final = git(repo, 'ls-tree', '-r', '--name-only', branch).split('\n')
    for commit in commits_do_pr(repo, base, branch):
        assunto = git(repo, 'log', '-1', '--format=%h "%s"', commit).strip()
        arquivo, numero = None, 0
        for linha in git(repo, 'show', '--format=', '--unified=0', '--no-color', commit).splitlines():
            if linha.startswith('+++ '):
                arquivo = linha[6:] if linha.startswith('+++ b/') else None
            elif linha.startswith('@@'):
                numero = int(re.search(r'\+(\d+)', linha).group(1))
            elif linha.startswith('+') and arquivo:
                for _, tipo, origem, chave in achar_segredos.achar(linha[1:]):
                    ainda = arquivo in final and chave in git(repo, 'show', f'{branch}:{arquivo}')
                    achados.append({'tipo': tipo, 'origem': origem, 'chave': achar_segredos.mascarar(chave),
                                    'onde': f'{arquivo}:{numero}', 'commit': assunto, 'no_final': ainda})
                numero += 1
    return achados


# 2. Dependências ---------------------------------------------------------------------------

GRAVIDADE = {'CRITICAL': 'crítica', 'HIGH': 'alta', 'MODERATE': 'média', 'MEDIUM': 'média', 'LOW': 'baixa'}


def normalizar(nome):
    return re.sub(r'[-_.]+', '-', nome).lower()


def versao(texto):
    return tuple(int(n) for n in re.findall(r'\d+', texto))


def afetada(aviso, nome, ver):
    for item in aviso.get('affected', []):
        pacote = item.get('package', {})
        if pacote.get('ecosystem') != 'PyPI' or normalizar(pacote.get('name', '')) != normalizar(nome):
            continue
        if ver in item.get('versions', []):
            return True
        for faixa in item.get('ranges', []):
            inicio, fim = None, None
            for evento in faixa.get('events', []):
                inicio = evento.get('introduced', inicio)
                fim = evento.get('fixed', fim)
            if inicio is not None and versao(ver) >= versao(inicio) and (fim is None or versao(ver) < versao(fim)):
                return True
    return False


def corrigida_em(aviso):
    fixos = [e['fixed'] for item in aviso.get('affected', []) for f in item.get('ranges', []) for e in f.get('events', []) if 'fixed' in e]
    return ', '.join(fixos) or 'sem versão corrigida'


def dependencias(repo, branch, pasta_avisos=AQUI / 'avisos'):
    """(problemas, quantas dependências). Problema: versão sem trava ou versão com aviso."""
    if 'requirements.txt' not in git(repo, 'ls-tree', '--name-only', branch).split('\n'):
        return [], 0
    avisos = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(Path(pasta_avisos).glob('*.json'))]
    problemas, total = [], 0
    for linha in git(repo, 'show', f'{branch}:requirements.txt').splitlines():
        linha = linha.split('#', 1)[0].strip()
        if not linha:
            continue
        total += 1
        m = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([0-9][0-9A-Za-z.]*)', linha)
        if not m:
            problemas.append(f'{linha}: versão não travada com ==, então ninguém sabe o que vai ser instalado')
            continue
        nome, ver = m.groups()
        for aviso in avisos:
            if afetada(aviso, nome, ver):
                gravidade = GRAVIDADE.get(aviso.get('database_specific', {}).get('severity', '').upper(), 'não informada')
                cves = ', '.join(a for a in aviso.get('aliases', []) if a.startswith('CVE-'))
                problemas.append(f'{nome} {ver}: {aviso["id"]} ({cves}), gravidade {gravidade}, '
                                 f'corrigida na {corrigida_em(aviso)}: {aviso.get("summary", "")}')
    return problemas, total


# 3 e 4. Código e testes, numa cópia da branch ----------------------------------------------

def codigo(pasta):
    return sast.analisar(pasta)


def testes(pasta):
    r = subprocess.run([sys.executable, '-m', 'unittest'], cwd=pasta, capture_output=True, text=True, timeout=900,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    saida = r.stdout + r.stderr
    rodou = re.search(r'Ran (\d+) tests?', saida)
    return r.returncode == 0, (rodou.group(1) if rodou else '0'), saida


def branch_atual(repo):
    return git(repo, 'rev-parse', '--abbrev-ref', 'HEAD').strip()


def rodar(repo, base, branch, mostrar=print):
    repo = Path(repo).resolve()
    lista = commits_do_pr(repo, base, branch)
    mostrar(f'Portão do PR: {branch} contra {base} ({len(lista)} commit(s))\n')
    falhas = 0

    mostrar('[1/4] segredos em cada commit do PR')
    achados = [a for a in segredos(repo, base, branch) if a['tipo'] == 'secreta']
    for a in achados:
        final = 'ainda no último commit' if a['no_final'] else 'o último commit não tem mais a chave'
        mostrar(f"  FALHOU  {a['origem']}  {a['chave']}  {a['onde']}  commit {a['commit']} ({final})")
    if not achados:
        mostrar('  passou  nenhuma chave secreta nos commits do PR')
    falhas += bool(achados)

    mostrar('[2/4] dependências do requirements.txt')
    problemas, total = dependencias(repo, branch)
    for p in problemas:
        mostrar('  FALHOU  ' + p)
    if not problemas:
        mostrar(f'  passou  {total} dependência(s), nenhuma com aviso' if total else '  passou  o PR não declara dependência')
    falhas += bool(problemas)

    with tempfile.TemporaryDirectory() as tmp:
        pasta = extrair(repo, branch, tmp)
        mostrar('[3/4] código (regras do sast.py)')
        achados_codigo = codigo(pasta)
        for a in achados_codigo:
            marca = 'ignorado' if a['ignorado'] else 'FALHOU '
            mostrar(f"  {marca} {a['regra']}  {a['arquivo']}:{a['linha']}  {a['funcao']}")
        abertos = [a for a in achados_codigo if not a['ignorado']]
        if not abertos:
            mostrar('  passou  nenhum achado aberto' + (f' ({len(achados_codigo)} ignorado com nosemgrep)' if achados_codigo else ''))
        falhas += bool(abertos)

        mostrar('[4/4] testes')
        ok, rodou, saida = testes(pasta)
        mostrar(f'  passou  {rodou} testes, OK' if ok else f'  FALHOU  {rodou} testes, com falha:\n' + '\n'.join(
            '    ' + l for l in saida.strip().splitlines()[-12:]))
        falhas += not ok

    mostrar('\nPR liberado: as 4 etapas passaram.' if not falhas else f'\nPR barrado: {falhas} de 4 etapas falharam.')
    return {'falhas': falhas, 'segredos': achados, 'dependencias': problemas, 'codigo': achados_codigo, 'testes': ok}


def main():
    parser = argparse.ArgumentParser(description='O portão do PR: segredos, dependências, código e testes.')
    parser.add_argument('repo', help='pasta do repositório git (por exemplo, repo-aurora)')
    parser.add_argument('--base', default='main', help='a branch que recebe o PR (padrão: main)')
    parser.add_argument('--branch', help='a branch do PR (padrão: a branch atual do repositório)')
    args = parser.parse_args()
    if not (Path(args.repo) / '.git').exists():
        sys.exit(f'{args.repo} não é um repositório git. Rode antes: python3 montar.py')
    resultado = rodar(args.repo, args.base, args.branch or branch_atual(args.repo))
    return 1 if resultado['falhas'] else 0


if __name__ == '__main__':
    sys.exit(main())
