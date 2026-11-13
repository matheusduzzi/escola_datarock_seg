"""Loja Aurora, versão da aula «Webhook, limite de requisições e consulta parametrizada».

É o app como ficou depois das aulas de autenticação e de IDOR (login pelo provedor, regra no
servidor, cada pedido visível só para o dono), com o que o agente do Diego acrescentou depois:
a busca com ordem e limite, a newsletter, o assistente de iluminação com IA e o webhook do
gateway de pagamento. As falhas dessa aula estão aí de propósito. Roda só em 127.0.0.1.

    python3 app.py            # sobe em http://127.0.0.1:8765
    python3 app.py --porta 9000
"""
import argparse
import json
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import dados  # noqa: E402
import modelo  # noqa: E402
import provedor  # noqa: E402

HOST = '127.0.0.1'
DESCONTO_CLUBE_PCT = 10
# CORS fechado para o nosso domínio: só o site da loja chama a API. (comentário do agente)
ORIGEM_DO_SITE = 'https://loja-aurora.example'


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


def agora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Loja:
    def __init__(self, banco, env):
        self.banco = Path(banco)
        self.env = env
        self.provedor = provedor.Provedor(dados.caminho_provedor(self.banco))
        self.modelo = modelo.Modelo(self.banco)

    def conectar(self):
        con = sqlite3.connect(self.banco)
        con.row_factory = sqlite3.Row
        return con

    def config_publica(self):
        publicas = {k: v for k, v in self.env.items() if k.startswith('PUBLIC_')}
        return 'window.AURORA = ' + json.dumps(publicas, ensure_ascii=False, indent=2) + ';\n'

    # Quem é ----------------------------------------------------------------------------------

    def login(self, email, senha):
        status, resposta = self.provedor.entrar(email, senha)
        if status == 429:
            return 429, {'erro': 'muitas tentativas; espere alguns minutos'}
        if status != 200:
            return 401, {'erro': 'e-mail ou senha incorretos'}
        usuario = self.usuario(resposta['user']['id'])
        if usuario is None:
            return 401, {'erro': 'e-mail ou senha incorretos'}
        return 200, {'token': resposta['access_token'], 'papel': usuario['papel']}

    def usuario(self, provedor_id):
        with self.conectar() as con:
            linha = con.execute('select id, nome, papel, plano, credito_centavos from usuarios where provedor_id = ?',
                                (provedor_id,)).fetchone()
        return dict(linha) if linha else None

    def sessao(self, token):
        quem = self.provedor.quem_e(token)
        return self.usuario(quem['id']) if quem else None

    def sair(self, token):
        return self.provedor.sair(token)

    def esqueci_senha(self, email):
        return self.provedor.pedir_nova_senha(email)

    def eu(self, sessao):
        if not sessao:
            return 401, {'erro': 'faça login'}
        return 200, {k: sessao.get(k) for k in ('nome', 'papel', 'plano', 'credito_centavos')}

    # Catálogo --------------------------------------------------------------------------------

    def buscar_produtos(self, busca, ordem='id', limite='100'):
        sql = ("select id, nome, categoria, preco_centavos from produtos where nome like '%" + busca + "%'"
               " order by " + ordem + " limit " + limite)
        with self.conectar() as con:
            return [dict(l) for l in con.execute(sql).fetchall()]

    # Pedidos ---------------------------------------------------------------------------------

    def criar_pedido(self, sessao, corpo):
        produto_id = int(corpo['produto_id'])
        quantidade = int(corpo.get('quantidade', 1))
        if quantidade < 1:
            return 400, {'erro': 'quantidade inválida'}
        with self.conectar() as con:
            produto = con.execute('select preco_centavos from produtos where id = ?', (produto_id,)).fetchone()
            if produto is None:
                return 404, {'erro': 'produto não encontrado'}
            preco = produto['preco_centavos']
            enviado = corpo.get('preco_centavos')
            if enviado is not None and enviado != preco:
                return 409, {'erro': 'o preço mudou; recarregue a página', 'preco_centavos': preco}
            conta = con.execute('select plano, credito_centavos from usuarios where id = ?', (sessao['id'],)).fetchone()
            subtotal = preco * quantidade
            desconto = subtotal * DESCONTO_CLUBE_PCT // 100 if conta['plano'] == 'clube' else 0
            credito = min(conta['credito_centavos'], subtotal - desconto)
            total = subtotal - desconto - credito
            baixa = con.execute('update usuarios set credito_centavos = credito_centavos - ? where id = ? and credito_centavos >= ?',
                                (credito, sessao['id'], credito))
            if baixa.rowcount != 1:
                return 409, {'erro': 'o saldo de crédito mudou; recarregue a página'}
            cur = con.execute(
                'insert into pedidos (cliente_id, produto_id, quantidade, desconto_centavos, credito_centavos, total_centavos, status)'
                ' values (?, ?, ?, ?, ?, ?, ?)',
                (sessao['id'], produto_id, quantidade, desconto, credito, total, 'aguardando pagamento'))
            return 201, {'pedido_id': cur.lastrowid, 'subtotal_centavos': subtotal, 'desconto_centavos': desconto,
                         'credito_centavos': credito, 'total_centavos': total}

    def ver_pedido(self, sessao, pedido_id):
        if not sessao:
            return 401, {'erro': 'faça login'}
        with self.conectar() as con:
            linha = con.execute('select * from pedidos where id = ?', (pedido_id,)).fetchone()
        if linha is None or (linha['cliente_id'] != sessao['id'] and sessao['papel'] != 'admin'):
            return 404, {'erro': 'pedido não encontrado'}   # o pedido de outra pessoa parece que não existe
        return 200, dict(linha)

    def guia_do_clube(self, sessao, consulta):
        if not sessao:
            return 401, {'erro': 'faça login'}
        if sessao['plano'] != 'clube':
            return 403, {'erro': 'conteúdo do Clube Aurora'}
        with self.conectar() as con:
            return 200, {'dicas': [l['dica'] for l in con.execute('select dica from guia_clube order by id')]}

    def pedidos_admin(self, sessao):
        if not sessao:
            return 401, {'erro': 'faça login'}
        if sessao['papel'] != 'admin':
            return 403, {'erro': 'só para administrador'}
        with self.conectar() as con:
            return 200, {'pedidos': [dict(l) for l in con.execute('select * from pedidos order by id')]}

    # Newsletter e assistente -----------------------------------------------------------------

    def inscrever_newsletter(self, corpo, ip):
        email = corpo.get('email', '')
        with self.conectar() as con:
            con.execute('insert into newsletter (email, ip, criado_em) values (?, ?, ?)', (email, ip, agora()))
        return 201, {'mensagem': 'inscrição recebida'}

    def assistente(self, sessao, corpo):
        pergunta = corpo.get('pergunta', '')
        usuario_id = sessao['id'] if sessao else None
        return 200, {'resposta': self.modelo.responder(pergunta, usuario_id)}

    # Webhooks --------------------------------------------------------------------------------

    def webhook_pagamento(self, cabecalhos, bruto):
        # O endereço não aparece no site: só o gateway conhece. (comentário do agente)
        corpo = json.loads(bruto or b'{}')
        with self.conectar() as con:
            con.execute('update pedidos set status = ? where id = ?', (corpo.get('status', 'pago'), int(corpo['pedido_id'])))
        return 200, {'ok': True}

    def webhook_pagafacil(self, bruto):
        # Integração com o PagaFácil, o gateway que a loja usava antes do atual.
        corpo = json.loads(bruto or b'{}')
        if corpo.get('status') == 'approved':
            with self.conectar() as con:
                con.execute("update pedidos set status = 'pago' where id = ?", (int(corpo['pedido_id']),))
        return 200, {'ok': True}


def criar_servidor(loja, porta):
    class Atendente(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            sys.stderr.write('[aurora] ' + (formato % args) + '\n')

        def responder(self, status, corpo, extras=None, tipo='application/json; charset=utf-8'):
            saida = corpo if isinstance(corpo, bytes) else (
                corpo.encode() if isinstance(corpo, str) else json.dumps(corpo, ensure_ascii=False).encode())
            self.send_response(status)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(saida)))
            self.send_header('Access-Control-Allow-Origin', ORIGEM_DO_SITE)
            for nome, valor in (extras or {}).items():
                self.send_header(nome, valor)
            self.end_headers()
            self.wfile.write(saida)

        def token(self):
            return self.headers.get('Authorization', '').replace('Bearer ', '', 1)

        def corpo(self):
            tamanho = int(self.headers.get('Content-Length') or 0)
            return self.rfile.read(tamanho) if tamanho else b''

        def do_GET(self):
            try:
                self.rotas_get()
            except Exception as erro:  # para facilitar o debug (comentário do agente)
                self.responder(500, {'erro': repr(erro), 'detalhe': traceback.format_exc()})

        def do_POST(self):
            try:
                self.rotas_post()
            except Exception as erro:  # para facilitar o debug (comentário do agente)
                self.responder(500, {'erro': repr(erro), 'detalhe': traceback.format_exc()})

        def rotas_get(self):
            url = urlparse(self.path)
            consulta = parse_qs(url.query)
            if url.path in ('/', '/index.html'):
                return self.responder(200, (AQUI / 'front' / 'index.html').read_bytes(), tipo='text/html; charset=utf-8')
            if url.path == '/config.js':
                return self.responder(200, loja.config_publica(), tipo='application/javascript; charset=utf-8')
            if url.path == '/api/produtos':
                busca = consulta.get('busca', [''])[0]
                ordem = consulta.get('ordem', ['id'])[0]
                limite = consulta.get('limite', ['100'])[0]
                try:
                    return self.responder(200, {'produtos': loja.buscar_produtos(busca, ordem, limite)})
                except sqlite3.Error as erro:
                    return self.responder(500, {'erro': str(erro)})
            if url.path == '/api/eu':
                return self.responder(*loja.eu(loja.sessao(self.token())))
            if url.path.startswith('/api/pedidos/'):
                return self.responder(*loja.ver_pedido(loja.sessao(self.token()), int(url.path.rsplit('/', 1)[1])))
            if url.path == '/api/clube/guia':
                return self.responder(*loja.guia_do_clube(loja.sessao(self.token()), url.query))
            if url.path == '/api/admin/pedidos':
                return self.responder(*loja.pedidos_admin(loja.sessao(self.token())))
            return self.responder(404, {'erro': 'rota não encontrada'})

        def rotas_post(self):
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
            if url.path == '/api/newsletter':
                return self.responder(*loja.inscrever_newsletter(json.loads(bruto or b'{}'), self.client_address[0]))
            if url.path == '/api/assistente':
                return self.responder(*loja.assistente(loja.sessao(self.token()), json.loads(bruto or b'{}')))
            if url.path == '/webhook/pagamento':
                return self.responder(*loja.webhook_pagamento(self.headers, bruto))
            if url.path == '/webhook/pagafacil':
                return self.responder(*loja.webhook_pagafacil(bruto))
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
