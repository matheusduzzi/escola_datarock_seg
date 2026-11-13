"""Monta os dois repositórios da aula e o painel de chaves dos provedores.

    python3 montar.py            # cria repo-aurora/, repo-assistente/ e painel.json
    python3 montar.py --de-novo  # apaga os três e cria de novo, do começo

Os repositórios são git de verdade, com o histórico que a equipe da Loja Aurora deixou.
As chaves são da loja do curso: não abrem conta nenhuma fora desta pasta.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

CHAVES = {
    'sk_aurora': 'aurora_sk_live_Vb8Nq2Lr6Tz4Yk1Wd9Hs3Qp7',
    'pk_aurora': 'aurora_pk_live_Gm5Rt8Xc2Nb6Lq9V',
    'mapa': 'aurora_mapa_pub_Hq3Ns8Vd1Kc',
    'llm': 'aurora_llm_sk_Pz4Kd7Wm2Rx9Tn5Bc8Lf3Jh6',
}

DIEGO = ('Diego', 'diego@aurora.example')
CARLA = ('Carla', 'carla@aurora.example')

CONFIG_PY = '''"""Lê a configuração: primeiro o arquivo .env, depois as variáveis do sistema (as do host vencem)."""
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def ler_env():
    valores = {}
    arquivo = AQUI / '.env'
    if arquivo.exists():
        for linha in arquivo.read_text(encoding='utf-8').splitlines():
            linha = linha.strip()
            if linha and not linha.startswith('#') and '=' in linha:
                nome, valor = linha.split('=', 1)
                valores[nome.strip()] = valor.strip()
    valores.update(os.environ)
    return valores
'''

BUILD_PY = '''"""Monta a pasta dist/, que é o que vai para o navegador de quem visita o site.

    python3 build.py               # grava em dist/
    python3 build.py --saida /tmp/x

Toda variável que começa com PUBLIC_ é copiada para dist/app.js, com o valor escrito no arquivo.
"""
import argparse
import json
import shutil
from pathlib import Path

from config import ler_env

AQUI = Path(__file__).resolve().parent


def montar(saida):
    saida = Path(saida)
    if saida.exists():
        shutil.rmtree(saida)
    saida.mkdir(parents=True)
    publicas = {k: v for k, v in sorted(ler_env().items()) if k.startswith('PUBLIC_')}
    js = 'const AURORA = ' + json.dumps(publicas, ensure_ascii=False, indent=2) + ';\\n\\n'
    js += (AQUI / 'front' / 'app.js').read_text(encoding='utf-8')
    (saida / 'app.js').write_text(js, encoding='utf-8')
    shutil.copy(AQUI / 'front' / 'index.html', saida / 'index.html')
    return publicas


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--saida', default=str(AQUI / 'dist'))
    args = parser.parse_args()
    publicas = montar(args.saida)
    print('dist pronto. Variáveis copiadas para o navegador: ' + ', '.join(publicas))
'''

SERVIDOR_PY = '''"""Serve a pasta dist/ e a rota {rota} em http://127.0.0.1:{porta}. Ctrl+C para parar.

    python3 build.py && python3 servidor.py
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import {modulo}

AQUI = Path(__file__).resolve().parent
TIPOS = {{'.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8'}}


class Atendente(BaseHTTPRequestHandler):
    def responder(self, status, corpo, tipo='application/json; charset=utf-8'):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        nome = 'index.html' if self.path in ('/', '/index.html') else self.path.lstrip('/')
        arquivo = AQUI / 'dist' / nome
        if '/' in nome or not arquivo.is_file():
            return self.responder(404, {{'erro': 'não encontrado'}})
        self.responder(200, arquivo.read_bytes(), TIPOS.get(arquivo.suffix, 'text/plain; charset=utf-8'))

    def do_POST(self):
        if self.path != '{rota}':
            return self.responder(404, {{'erro': 'rota não encontrada'}})
        self.responder(200, {modulo}.responder())


if __name__ == '__main__':
    if not (AQUI / 'dist' / 'index.html').exists():
        sys.exit('Rode python3 build.py antes.')
    print('Site em http://127.0.0.1:{porta} (Ctrl+C para parar)')
    try:
        ThreadingHTTPServer(('127.0.0.1', {porta}), Atendente).serve_forever()
    except KeyboardInterrupt:
        pass
'''

INDEX_HTML = '''<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title></head>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem">
<h1 id="nome">{titulo}</h1>
<p id="status">Carregando...</p>
<button id="acao">{botao}</button>
<script src="/app.js"></script>
</body>
</html>
'''

AURORA_APP_JS = '''// Vitrine e checkout da Loja Aurora.
document.getElementById('nome').textContent = AURORA.PUBLIC_LOJA_NOME;
document.getElementById('status').textContent = 'Pagamento com a chave pública ' + AURORA.PUBLIC_PAGAMENTO_CHAVE_PUBLICA.slice(0, 15) + '...';
document.getElementById('acao').addEventListener('click', async () => {
  const r = await fetch('/api/pagar', {method: 'POST'});
  document.getElementById('status').textContent = JSON.stringify(await r.json());
});
'''

ASSISTENTE_APP_JS = '''// Assistente de produtos da Loja Aurora.
document.getElementById('nome').textContent = AURORA.PUBLIC_LOJA_NOME;
document.getElementById('status').textContent = AURORA.PUBLIC_IA_CHAVE
  ? 'O navegador chama o provedor de IA direto, com a chave.'
  : 'O navegador pede ao servidor, e o servidor chama o provedor de IA.';
document.getElementById('acao').addEventListener('click', async () => {
  const r = await fetch('/api/assistente', {method: 'POST'});
  document.getElementById('status').textContent = JSON.stringify(await r.json());
});
'''

PAGAMENTO_FIXO = '''"""Cobrança no gateway de pagamento. Roda só no servidor."""

CHAVE_SECRETA = '{sk}'


def responder():
    return {{'ok': bool(CHAVE_SECRETA), 'final_da_chave': CHAVE_SECRETA[-4:]}}
'''

PAGAMENTO_ENV = '''"""Cobrança no gateway de pagamento. Roda só no servidor."""
from config import ler_env

CHAVE_SECRETA = ler_env().get('PUBLIC_PAGAMENTO_CHAVE_SECRETA', '')


def responder():
    return {'ok': bool(CHAVE_SECRETA), 'final_da_chave': CHAVE_SECRETA[-4:]}
'''

ASSISTENTE_PY = '''"""Chamada ao provedor de IA pelo servidor."""
from config import ler_env

CHAVE = ler_env().get('IA_CHAVE', '')


def responder():
    if not CHAVE:
        return {'ok': False, 'erro': 'falta IA_CHAVE no servidor'}
    return {'ok': True, 'resposta': 'A luminária Lua cabe em mesa de cabeceira de 40 cm.'}
'''

DOCKERFILE = '''FROM python:3.12-slim
WORKDIR /app
COPY . .
CMD ["sh", "-c", "python3 build.py && python3 servidor.py"]
'''

GITIGNORE_AURORA = 'node_modules/\ndist/\n.DS_Store\n*.log\n'
GITIGNORE_ASSISTENTE = '# Arquivos locais\n*.local\ndist/\n__pycache__/\n'


def env_aurora(sk):
    return ('PUBLIC_LOJA_NOME=Loja Aurora\n'
            f'PUBLIC_MAPA_CHAVE={CHAVES["mapa"]}\n'
            f'PUBLIC_PAGAMENTO_CHAVE_PUBLICA={CHAVES["pk_aurora"]}\n'
            f'PUBLIC_PAGAMENTO_CHAVE_SECRETA={sk}\n')


EXEMPLO_AURORA = ('# Copie para .env e preencha. Nunca ponha valor de verdade aqui.\n'
                  'PUBLIC_LOJA_NOME=Loja Aurora\nPUBLIC_MAPA_CHAVE=\nPUBLIC_PAGAMENTO_CHAVE_PUBLICA=\n'
                  'PUBLIC_PAGAMENTO_CHAVE_SECRETA=\n')
ENV_ASSISTENTE = f'PUBLIC_LOJA_NOME=Loja Aurora\nPUBLIC_IA_CHAVE={CHAVES["llm"]}\n'
EXEMPLO_ASSISTENTE = '# Copie para .env e preencha.\nPUBLIC_LOJA_NOME=Loja Aurora\nPUBLIC_IA_CHAVE=\n'


def base(titulo, botao, rota, modulo, app_js, readme):
    return {
        'README.md': readme,
        'config.py': CONFIG_PY,
        'build.py': BUILD_PY,
        'servidor.py': SERVIDOR_PY.format(rota=rota, porta=8790 if modulo == 'pagamento' else 8791, modulo=modulo),
        'front/index.html': INDEX_HTML.format(titulo=titulo, botao=botao),
        'front/app.js': app_js,
        'Dockerfile': DOCKERFILE,
    }


README_AURORA = '# Site da Loja Aurora\n\nVitrine e checkout.\n\n```\npython3 build.py\npython3 servidor.py\n```\n'
README_ASSISTENTE = '# Assistente de produtos da Loja Aurora\n\nResponde dúvidas sobre as luminárias.\n\n```\npython3 build.py\npython3 servidor.py\n```\n'

REPOS = {
    'repo-aurora': [
        ('main', DIEGO, '2026-09-02T10:00:00-03:00', 'Primeira versão do site', {
            **base('Loja Aurora', 'Pagar', '/api/pagar', 'pagamento', AURORA_APP_JS, README_AURORA),
            '.gitignore': GITIGNORE_AURORA, '.env.exemplo': EXEMPLO_AURORA,
            'pagamento.py': PAGAMENTO_FIXO.format(sk=''),
        }, []),
        ('main', DIEGO, '2026-09-09T15:20:00-03:00', 'Liga o pagamento', {
            'pagamento.py': PAGAMENTO_FIXO.format(sk=CHAVES['sk_aurora']),
        }, []),
        ('main', DIEGO, '2026-09-16T11:05:00-03:00', 'Tira a chave do código', {
            'pagamento.py': PAGAMENTO_ENV, '.env': env_aurora(CHAVES['sk_aurora']),
        }, []),
    ],
    'repo-assistente': [
        ('main', CARLA, '2026-10-01T09:30:00-03:00', 'Primeira versão do assistente', {
            **base('Assistente da Loja Aurora', 'Perguntar', '/api/assistente', 'assistente', ASSISTENTE_APP_JS, README_ASSISTENTE),
            '.gitignore': GITIGNORE_ASSISTENTE, '.env.exemplo': EXEMPLO_ASSISTENTE, 'assistente.py': ASSISTENTE_PY,
        }, []),
        ('teste-ia', CARLA, '2026-10-06T17:45:00-03:00', 'Teste com o provedor de IA', {
            '.env': ENV_ASSISTENTE,
        }, []),
        ('main', CARLA, '2026-10-08T10:10:00-03:00', 'Texto do botão', {
            'front/index.html': INDEX_HTML.format(titulo='Assistente da Loja Aurora', botao='Perguntar ao assistente'),
        }, []),
    ],
}

# Arquivos que ficam na pasta, fora do git, depois do último commit.
SOLTOS = {'repo-assistente': {'.env': ENV_ASSISTENTE}}

PAINEL = {
    'chaves': [
        {'provedor': 'gateway', 'tipo': 'pública', 'valor': CHAVES['pk_aurora'], 'criada': '2026-09-09', 'estado': 'ativa'},
        {'provedor': 'gateway', 'tipo': 'secreta', 'valor': CHAVES['sk_aurora'], 'criada': '2026-09-09', 'estado': 'ativa'},
        {'provedor': 'mapa', 'tipo': 'pública', 'valor': CHAVES['mapa'], 'criada': '2026-09-02', 'estado': 'ativa'},
        {'provedor': 'ia', 'tipo': 'secreta', 'valor': CHAVES['llm'], 'criada': '2026-10-06', 'estado': 'ativa'},
    ]
}


def git(pasta, *args, data=None, autor=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    if autor:
        env.update(GIT_AUTHOR_NAME=autor[0], GIT_AUTHOR_EMAIL=autor[1], GIT_COMMITTER_NAME=autor[0],
                   GIT_COMMITTER_EMAIL=autor[1], GIT_AUTHOR_DATE=data, GIT_COMMITTER_DATE=data)
    return subprocess.run(['git', '-c', 'init.defaultBranch=main', '-c', 'commit.gpgsign=false', *args],
                          cwd=pasta, env=env, check=True, capture_output=True, text=True).stdout


def montar_repo(pasta, commits):
    pasta.mkdir()
    git(pasta, 'init', '-q', '--object-format=sha1')
    for branch, autor, data, mensagem, arquivos, _ in commits:
        atual = git(pasta, 'branch', '--show-current').strip()
        tem_commit = subprocess.run(['git', 'rev-parse', '-q', '--verify', 'HEAD'], cwd=pasta, capture_output=True).returncode == 0
        if tem_commit and branch != atual:
            existe = subprocess.run(['git', 'rev-parse', '-q', '--verify', branch], cwd=pasta, capture_output=True).returncode == 0
            git(pasta, 'checkout', '-q', branch) if existe else git(pasta, 'checkout', '-q', '-b', branch)
        for nome, texto in arquivos.items():
            caminho = pasta / nome
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(texto, encoding='utf-8')
        git(pasta, 'add', '.')
        git(pasta, 'commit', '-q', '-m', mensagem, data=data, autor=autor)
    git(pasta, 'checkout', '-q', 'main')
    git(pasta, 'config', 'user.name', 'Você')
    git(pasta, 'config', 'user.email', 'voce@aurora.example')


def main():
    parser = argparse.ArgumentParser(description='Monta os repositórios da aula e o painel de chaves.')
    parser.add_argument('--de-novo', action='store_true', help='apaga o que já existe e monta do começo')
    parser.add_argument('--pasta', default=str(AQUI), help='onde montar (padrão: esta pasta)')
    args = parser.parse_args()
    destino = Path(args.pasta).resolve()
    alvos = [destino / n for n in REPOS] + [destino / 'painel.json']
    if any(a.exists() for a in alvos):
        if not args.de_novo:
            print('Já existe repo-aurora/, repo-assistente/ ou painel.json aqui. Use --de-novo para começar de novo.')
            return 1
        for a in alvos:
            shutil.rmtree(a) if a.is_dir() else a.unlink(missing_ok=True)
    for nome, commits in REPOS.items():
        montar_repo(destino / nome, commits)
        for arquivo, texto in SOLTOS.get(nome, {}).items():
            (destino / nome / arquivo).write_text(texto, encoding='utf-8')
        print(f'{nome}: {len(commits)} commits')
    (destino / 'painel.json').write_text(json.dumps(PAINEL, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('painel.json: 4 chaves ativas (gateway, mapa e provedor de IA)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
