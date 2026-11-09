"""Loja Aurora, versão da aula «Autenticação pronta e regra no servidor».

É o app do curso com o Clube Aurora, o crédito de troca e o painel da Renata, do jeito que o
agente do Diego escreveu. Tem falhas de propósito, para você achar e corrigir. Roda só no seu
computador, em 127.0.0.1. Não publique este app nem copie trechos dele para um projeto real.

    python3 app.py            # sobe em http://127.0.0.1:8765
    python3 app.py --porta 9000
"""
import argparse
import json
import secrets
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import dados  # noqa: E402
import provedor  # noqa: E402

HOST = '127.0.0.1'
DESCONTO_CLUBE_PCT = 10


def ler_env(pasta=AQUI):
    """Lê o .env da pasta; sem ele, usa o .env.exemplo."""
    arquivo = pasta / '.env' if (pasta / '.env').exists() else pasta / '.env.exemplo'
    valores = {}
    for linha in arquivo.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if linha and not linha.startswith('#') and '=' in linha:
            chave, valor = linha.split('=', 1)
            valores[chave.strip()] = valor.strip()
    return valores


class Loja:
    def __init__(self, banco, env):
        self.banco = Path(banco)
        self.env = env
        # O Diego já criou a conta no provedor e importou os usuários. O login ainda não usa.
        self.provedor = provedor.Provedor(dados.caminho_provedor(self.banco))
        self.sessoes = {}

    def conectar(self):
        con = sqlite3.connect(self.banco)
        con.row_factory = sqlite3.Row
        return con

    def config_publica(self):
        publicas = {k: v for k, v in self.env.items() if k.startswith('PUBLIC_')}
        return 'window.AURORA = ' + json.dumps(publicas, ensure_ascii=False, indent=2) + ';\n'

    # Quem é ----------------------------------------------------------------------------------

    def login(self, email, senha):
        if email == 'admin@aurora.example' and senha == 'Aurora@2026':
            token = secrets.token_hex(16)
            self.sessoes[token] = {'id': None, 'nome': 'Administrador', 'papel': 'admin', 'plano': 'gratis', 'credito_centavos': 0}
            return 200, {'token': token, 'papel': 'admin'}
        with self.conectar() as con:
            linha = con.execute('select * from usuarios where email = ?', (email,)).fetchone()
        if linha is None:
            return 404, {'erro': 'e-mail não cadastrado'}
        if dados.hash_senha(senha, bytes.fromhex(linha['sal'])) != linha['senha_hash']:
            return 401, {'erro': 'senha incorreta'}
        token = secrets.token_hex(16)
        self.sessoes[token] = dict(linha)
        return 200, {'token': token, 'papel': linha['papel']}

    def sessao(self, token):
        return self.sessoes.get(token)

    def sair(self, token):
        self.sessoes.pop(token, None)
        return 200, {'ok': True}

    def esqueci_senha(self, email):
        with self.conectar() as con:
            linha = con.execute('select id from usuarios where email = ?', (email,)).fetchone()
        if linha is None:
            return 404, {'erro': 'não existe conta com esse e-mail'}
        return 200, {'mensagem': 'enviamos um link para o seu e-mail'}

    def eu(self, sessao):
        if not sessao:
            return 401, {'erro': 'faça login'}
        return 200, {k: sessao.get(k) for k in ('nome', 'papel', 'plano', 'credito_centavos')}

    # O que pode -----------------------------------------------------------------------------

    def buscar_produtos(self, busca):
        sql = "select id, nome, categoria, preco_centavos from produtos where nome like '%" + busca + "%' order by id"
        with self.conectar() as con:
            return [dict(l) for l in con.execute(sql).fetchall()]

    def criar_pedido(self, sessao, corpo):
        produto_id = int(corpo['produto_id'])
        quantidade = int(corpo.get('quantidade', 1))
        if quantidade < 1:
            return 400, {'erro': 'quantidade inválida'}
        with self.conectar() as con:
            produto = con.execute('select preco_centavos from produtos where id = ?', (produto_id,)).fetchone()
            if produto is None:
                return 404, {'erro': 'produto não encontrado'}
            preco = int(corpo.get('preco_centavos', produto['preco_centavos']))
            subtotal = preco * quantidade
            desconto = subtotal * DESCONTO_CLUBE_PCT // 100 if corpo.get('plano') == 'clube' else 0
            credito = min(int(corpo.get('credito_centavos', 0)), subtotal - desconto)
            total = subtotal - desconto - credito
            cur = con.execute(
                'insert into pedidos (cliente_id, produto_id, quantidade, desconto_centavos, credito_centavos, total_centavos, status)'
                ' values (?, ?, ?, ?, ?, ?, ?)',
                (sessao['id'], produto_id, quantidade, desconto, credito, total, 'aguardando pagamento'))
            return 201, {'pedido_id': cur.lastrowid, 'subtotal_centavos': subtotal, 'desconto_centavos': desconto,
                         'credito_centavos': credito, 'total_centavos': total}

    def ver_pedido(self, pedido_id):
        with self.conectar() as con:
            linha = con.execute('select * from pedidos where id = ?', (pedido_id,)).fetchone()
        return dict(linha) if linha else None

    def guia_do_clube(self, sessao, consulta):
        if not sessao:
            return 401, {'erro': 'faça login'}
        if parse_qs(consulta).get('plano', [''])[0] != 'clube':
            return 403, {'erro': 'conteúdo do Clube Aurora'}
        with self.conectar() as con:
            return 200, {'dicas': [l['dica'] for l in con.execute('select dica from guia_clube order by id')]}

    def pedidos_admin(self, sessao):
        # O link do painel só aparece na tela para quem é admin (front/index.html).
        with self.conectar() as con:
            return 200, {'pedidos': [dict(l) for l in con.execute('select * from pedidos order by id')]}

    def webhook_pagamento(self, cabecalhos, bruto):
        corpo = json.loads(bruto or b'{}')
        with self.conectar() as con:
            con.execute('update pedidos set status = ? where id = ?', (corpo.get('status', 'pago'), int(corpo['pedido_id'])))
        return 200, {'ok': True}


def criar_servidor(loja, porta):
    class Atendente(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            sys.stderr.write('[aurora] ' + (formato % args) + '\n')

        def responder(self, status, corpo, tipo='application/json; charset=utf-8'):
            saida = corpo if isinstance(corpo, bytes) else (
                corpo.encode() if isinstance(corpo, str) else json.dumps(corpo, ensure_ascii=False).encode())
            self.send_response(status)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(saida)))
            self.end_headers()
            self.wfile.write(saida)

        def token(self):
            return self.headers.get('Authorization', '').replace('Bearer ', '', 1)

        def corpo(self):
            tamanho = int(self.headers.get('Content-Length') or 0)
            return self.rfile.read(tamanho) if tamanho else b''

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ('/', '/index.html'):
                return self.responder(200, (AQUI / 'front' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            if url.path == '/config.js':
                return self.responder(200, loja.config_publica(), 'application/javascript; charset=utf-8')
            if url.path == '/api/produtos':
                busca = parse_qs(url.query).get('busca', [''])[0]
                try:
                    return self.responder(200, {'produtos': loja.buscar_produtos(busca)})
                except sqlite3.Error as erro:
                    return self.responder(500, {'erro': str(erro)})
            if url.path == '/api/eu':
                return self.responder(*loja.eu(loja.sessao(self.token())))
            if url.path.startswith('/api/pedidos/'):
                pedido = loja.ver_pedido(int(url.path.rsplit('/', 1)[1]))
                return self.responder(200, pedido) if pedido else self.responder(404, {'erro': 'pedido não encontrado'})
            if url.path == '/api/clube/guia':
                return self.responder(*loja.guia_do_clube(loja.sessao(self.token()), url.query))
            if url.path == '/api/admin/pedidos':
                return self.responder(*loja.pedidos_admin(loja.sessao(self.token())))
            return self.responder(404, {'erro': 'rota não encontrada'})

        def do_POST(self):
            url = urlparse(self.path)
            bruto = self.corpo()
            if url.path == '/api/login':
                corpo = json.loads(bruto or b'{}')
                return self.responder(*loja.login(corpo.get('email', ''), corpo.get('senha', '')))
            if url.path == '/api/sair':
                return self.responder(*loja.sair(self.token()))
            if url.path == '/api/esqueci-senha':
                return self.responder(*loja.esqueci_senha(json.loads(bruto or b'{}').get('email', '')))
            if url.path == '/api/pedidos':
                sessao = loja.sessao(self.token())
                if not sessao:
                    return self.responder(401, {'erro': 'faça login'})
                return self.responder(*loja.criar_pedido(sessao, json.loads(bruto or b'{}')))
            if url.path == '/webhook/pagamento':
                return self.responder(*loja.webhook_pagamento(self.headers, bruto))
            return self.responder(404, {'erro': 'rota não encontrada'})

    return ThreadingHTTPServer((HOST, porta), Atendente)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--banco', default=str(AQUI / 'aurora.db'))
    args = parser.parse_args()
    if not Path(args.banco).exists() or not dados.caminho_provedor(args.banco).exists():
        dados.montar(args.banco)
    servidor = criar_servidor(Loja(args.banco, ler_env()), args.porta)
    print(f'Loja Aurora em http://{HOST}:{args.porta} (Ctrl+C para parar)')
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
