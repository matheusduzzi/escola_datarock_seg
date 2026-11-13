"""Diz, item por item, o que já está fechado num dos repositórios da aula.

    python3 checar.py repo-aurora
    python3 checar.py repo-assistente

Olha o que o git guarda agora (o próximo commit). Sai com 0 quando os seis itens estão fechados
e com 1 enquanto algum continua aberto.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import achar_segredos  # noqa: E402

# Onde cada repositório guarda a chave que o servidor usa.
SERVIDOR = {'repo-aurora': ('pagamento', 'CHAVE_SECRETA'), 'repo-assistente': ('assistente', 'CHAVE')}
IGNORA_ENV = {'.env', '.env*', '*.env', '**/.env', '.env.*'}
# O build e o servidor rodam sem as variáveis da aula que estiverem no seu terminal: vale só o .env.
LIMPO = {k: v for k, v in os.environ.items() if not k.startswith('PUBLIC_') and k not in ('PAGAMENTO_CHAVE_SECRETA', 'IA_CHAVE')}
LIMPO['PYTHONDONTWRITEBYTECODE'] = '1'


def git(pasta, *args):
    return subprocess.run(['git', *args], cwd=pasta, capture_output=True, text=True)


def ler_env(arquivo):
    valores = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding='utf-8').splitlines():
            if '=' in linha and not linha.strip().startswith('#'):
                nome, valor = linha.split('=', 1)
                valores[nome.strip()] = valor.strip()
    return valores


def secretas(texto):
    return [chave for _, tipo, _, chave in achar_segredos.achar(texto) if tipo == 'secreta']


def chave_do_servidor(pasta, modulo, atributo):
    """Carrega o módulo do servidor como ele roda, num processo separado, e devolve a chave que ele leu."""
    codigo = f'import sys; sys.path.insert(0, "."); import {modulo}; print({modulo}.{atributo})'
    r = subprocess.run([sys.executable, '-c', codigo], cwd=pasta, capture_output=True, text=True,
                       env=LIMPO)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description='Checa os itens da aula num repositório.')
    parser.add_argument('repo', choices=sorted(SERVIDOR))
    parser.add_argument('--painel', default=str(AQUI / 'painel.json'))
    args = parser.parse_args()
    pasta = (AQUI / args.repo).resolve()
    if not (pasta / '.git').is_dir():
        sys.exit(f'Não achei {pasta}. Rode python3 montar.py antes.')
    painel = {c['valor']: c for c in json.loads(Path(args.painel).read_text(encoding='utf-8'))['chaves']}
    env = ler_env(pasta / '.env')
    itens = []

    historico = achar_segredos.no_historico(pasta)
    vazadas = sorted({a[2] for a in historico if a[0] == 'secreta'})
    ativas = [achar_segredos.mascarar(c) for c in vazadas if painel.get(c, {}).get('estado') != 'revogada']
    itens.append(('chave do histórico revogada', not ativas,
                  f'continua ativa no painel: {", ".join(ativas)}' if ativas else
                  f'{len(vazadas)} chave(s) secreta(s) do histórico, todas revogadas no painel'))

    # O índice é o que vai no próximo commit; depois do commit, é igual ao último commit.
    atual = git(pasta, 'grep', '--cached', '-I', '-n', '-E', achar_segredos.UNIAO).stdout
    no_git = sorted({linha.split(':', 2)[0] for linha in atual.splitlines() if secretas(linha.split(':', 2)[2])})
    itens.append(('git sem chave secreta', not no_git,
                  f'o git ainda guarda {", ".join(no_git)}, com chave secreta' if no_git else 'nenhum arquivo que o git guarda tem chave secreta'))

    rastreado = bool(git(pasta, 'ls-files', '--error-unmatch', '.env').returncode == 0)
    ignorado = git(pasta, 'check-ignore', '-q', '--no-index', '.env').returncode == 0
    exemplo_ignorado = git(pasta, 'check-ignore', '-q', '--no-index', '.env.exemplo').returncode == 0
    exemplo_ok = not secretas((pasta / '.env.exemplo').read_text(encoding='utf-8')) if (pasta / '.env.exemplo').exists() else False
    ok = ignorado and not rastreado and not exemplo_ignorado and exemplo_ok
    motivo = ('o .env está no git' if rastreado else 'o .gitignore não ignora o .env' if not ignorado else
              'o .gitignore também esconde o .env.exemplo' if exemplo_ignorado else
              'o .env.exemplo sumiu ou tem chave secreta' if not exemplo_ok else
              'o .env está fora do git e o .gitignore ignora; o .env.exemplo continua no repositório')
    itens.append(('.env fora do git', ok, motivo))

    docker = pasta / '.dockerignore'
    linhas = {l.strip() for l in docker.read_text(encoding='utf-8').splitlines()} if docker.exists() else set()
    itens.append(('.env fora da imagem Docker', bool(linhas & IGNORA_ENV),
                  'o .dockerignore lista o .env' if linhas & IGNORA_ENV else
                  ('o .dockerignore não lista o .env' if docker.exists() else 'não tem .dockerignore: o COPY . . leva o .env para a imagem')))

    publicas_secretas = [n for n, v in env.items() if n.startswith('PUBLIC_') and secretas(v)]
    itens.append(('chave secreta sem PUBLIC_', not publicas_secretas,
                  f'{", ".join(publicas_secretas)} tem chave secreta e vai para o navegador' if publicas_secretas else
                  'nenhuma variável PUBLIC_ do .env tem chave secreta'))

    modulo, atributo = SERVIDOR[args.repo]
    usada = chave_do_servidor(pasta, modulo, atributo)
    with tempfile.TemporaryDirectory() as tmp:
        build = subprocess.run([sys.executable, 'build.py', '--saida', tmp], cwd=pasta, capture_output=True, text=True,
                               env=LIMPO)
        js = (Path(tmp) / 'app.js').read_text(encoding='utf-8') if build.returncode == 0 else ''
    no_front = secretas(js)
    montado = pasta / 'dist' / 'app.js'
    velho = secretas(montado.read_text(encoding='utf-8')) if montado.exists() else []
    usada_ok = bool(usada) and painel.get(usada, {}).get('estado') == 'ativa' and usada not in js
    if build.returncode != 0 or 'Loja Aurora' not in js:
        motivo, ok = 'o build quebrou ou não levou o nome da loja para o navegador', False
    elif no_front:
        motivo, ok = 'o app.js que vai para o navegador tem chave secreta (' + ', '.join(map(achar_segredos.mascarar, no_front)) + ')', False
    elif velho:
        motivo, ok = 'a configuração está certa, mas o dist/ que você montou antes ainda tem a chave: rode python3 build.py de novo', False
    elif not usada_ok:
        motivo, ok = 'o servidor não lê uma chave ativa do painel: o site para de funcionar', False
    else:
        motivo, ok = f'o app.js não tem chave secreta e o servidor usa a chave ativa (final {usada[-4:]})', True
    itens.append(('navegador sem chave secreta', ok, motivo))

    for nome, fechado, texto in itens:
        print(f'{"fechado" if fechado else "ABERTO ":7}  {nome}: {texto}')
    fechados = sum(1 for _, f, _ in itens if f)
    print(f'\n{fechados} de {len(itens)} fechados.')
    restantes = [a for a in historico if a[0] == 'secreta']
    if restantes and not ativas:
        commits = len({a[4].split()[1] for a in restantes})
        print(f'Para saber: o histórico ainda guarda a chave revogada em {commits} commit(s). Revogada, ela não abre nada.')
    return 0 if fechados == len(itens) else 1


if __name__ == '__main__':
    sys.exit(main())
