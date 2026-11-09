"""Loja Aurora da aula «Quem vê e quem muda o quê: IDOR e mass assignment».

O login já passa pelo provedor e preço, plano, crédito e painel já são decididos no servidor
(aula «Autenticação pronta e regra no servidor»). As rotas novas que o agente do Diego escreveu
para "Meus pedidos", a nota do pedido e o perfil têm falhas de propósito: são o assunto dessa aula.
App de treino: escuta só em 127.0.0.1 e não deve ser publicado.

    python3 app.py            # sobe em http://127.0.0.1:8765
    python3 app.py --porta 9000
"""
import argparse
import json
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import bucket  # noqa: E402
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
        self.provedor = provedor.Provedor(dados.caminho_provedor(self.banco))
        # O bucket das notas dos pedidos. O agente criou como público "para o link funcionar".
        self.notas = bucket.Bucket(dados.caminho_notas(self.banco), publico=True)

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
        return 200, {'token': resposta['access_token']}

    def usuario(self, provedor_id):
        with self.conectar() as con:
            linha = con.execute('select id, nome, email, plano, is_admin, creditos from usuarios where provedor_id = ?',
                                (provedor_id,)).fetchone()
        return dict(linha) if linha else None

    def sessao(self, token):
        """Quem é vem do provedor; o que pode (plano, crédito, is_admin) vem do banco do app, a cada pedido."""
        quem = self.provedor.quem_e(token)
        return self.usuario(quem['id']) if quem else None

    def sair(self, token):
        return self.provedor.sair(token)

    def esqueci_senha(self, email):
        return self.provedor.pedir_nova_senha(email)

    def eu(self, sessao):
        return 200, {k: sessao[k] for k in ('nome', 'email', 'plano', 'creditos', 'is_admin')}

    # Loja ------------------------------------------------------------------------------------

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
            preco = produto['preco_centavos']
            enviado = corpo.get('preco_centavos')
            if enviado is not None and enviado != preco:
                return 409, {'erro': 'o preço mudou; recarregue a página', 'preco_centavos': preco}
            conta = con.execute('select plano, creditos from usuarios where id = ?', (sessao['id'],)).fetchone()
            subtotal = preco * quantidade
            desconto = subtotal * DESCONTO_CLUBE_PCT // 100 if conta['plano'] == 'clube' else 0
            credito = min(conta['creditos'], subtotal - desconto)
            total = subtotal - desconto - credito
            baixa = con.execute('update usuarios set creditos = creditos - ? where id = ? and creditos >= ?',
                                (credito, sessao['id'], credito))
            if baixa.rowcount != 1:
                return 409, {'erro': 'o saldo de crédito mudou; recarregue a página'}
            endereco = corpo.get('endereco') or 'retirar na loja'
            cur = con.execute(
                'insert into pedidos (cliente_id, produto_id, quantidade, desconto_centavos, credito_centavos, total_centavos, status, endereco)'
                ' values (?, ?, ?, ?, ?, ?, ?, ?)',
                (sessao['id'], produto_id, quantidade, desconto, credito, total, 'aguardando pagamento', endereco))
            return 201, {'pedido_id': cur.lastrowid, 'subtotal_centavos': subtotal, 'desconto_centavos': desconto,
                         'credito_centavos': credito, 'total_centavos': total}

    def meus_pedidos(self, sessao):
        with self.conectar() as con:
            linhas = con.execute('select p.id, d.nome as produto, p.quantidade, p.total_centavos, p.status from pedidos p'
                                 ' join produtos d on d.id = p.produto_id where p.cliente_id = ? order by p.id',
                                 (sessao['id'],)).fetchall()
        return 200, {'pedidos': [dict(l) for l in linhas]}

    def ver_pedido(self, sessao, pedido_id):
        with self.conectar() as con:
            linha = con.execute('select p.id, u.nome as cliente, d.nome as produto, p.quantidade, p.total_centavos,'
                                ' p.status, p.endereco from pedidos p join usuarios u on u.id = p.cliente_id'
                                ' join produtos d on d.id = p.produto_id where p.id = ?', (pedido_id,)).fetchone()
        if linha is None:
            return 404, {'erro': 'pedido não encontrado'}
        return 200, dict(linha)

    def nota_do_pedido(self, sessao, pedido_id):
        with self.conectar() as con:
            linha = con.execute('select nota from pedidos where id = ?', (pedido_id,)).fetchone()
        if linha is None or not linha['nota']:
            return 404, {'erro': 'nota não encontrada'}
        return 200, {'url': self.notas.url_publica(linha['nota'])}

    def baixar_arquivo(self, arquivo, consulta):
        return self.notas.baixar(arquivo, consulta)

    # Perfil ----------------------------------------------------------------------------------

    def buscar_usuario(self, sessao, email):
        with self.conectar() as con:
            linha = con.execute('select * from usuarios where email = ?', (email,)).fetchone()
        if linha is None:
            return 404, {'erro': 'usuário não encontrado'}
        return 200, dict(linha)

    def atualizar_perfil(self, sessao, corpo):
        if not isinstance(corpo, dict) or not corpo:
            return 400, {'erro': 'nada para atualizar'}
        # O dono é quem entrou: o "where id = ?" usa o id da sessão, não um id do corpo.
        sets = ', '.join(campo + ' = ?' for campo in corpo)
        try:
            with self.conectar() as con:
                con.execute('update usuarios set ' + sets + ' where id = ?', (*corpo.values(), sessao['id']))
        except sqlite3.Error as erro:
            return 400, {'erro': str(erro)}
        return 200, {'ok': True}

    # Clube e painel --------------------------------------------------------------------------

    def guia_do_clube(self, sessao):
        if sessao['plano'] != 'clube':
            return 403, {'erro': 'conteúdo do Clube Aurora'}
        with self.conectar() as con:
            return 200, {'dicas': [l['dica'] for l in con.execute('select dica from guia_clube order by id')]}

    def pedidos_admin(self, sessao):
        if not sessao['is_admin']:
            return 403, {'erro': 'só para administrador'}
        with self.conectar() as con:
            return 200, {'pedidos': [dict(l) for l in con.execute('select * from pedidos order by id')]}

    def webhook_pagamento(self, cabecalhos, bruto):
        corpo = json.loads(bruto or b'{}')
        with self.conectar() as con:
            con.execute('update pedidos set status = ? where id = ?', (corpo.get('status', 'pago'), int(corpo['pedido_id'])))
        return 200, {'ok': True}


ROTA_PEDIDO = re.compile(r'^/api/pedidos/(\d+)$')
ROTA_NOTA = re.compile(r'^/api/pedidos/(\d+)/nota$')
ROTA_ARQUIVO = re.compile(r'^/arquivos/notas/([^/]+)$')


def criar_servidor(loja, porta):
    class Atendente(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            sys.stderr.write('[aurora] ' + (formato % args) + '\n')

        def responder(self, status, corpo, tipo='application/json; charset=utf-8'):
            if isinstance(corpo, bytes) and tipo.startswith('application/json'):
                tipo = 'text/plain; charset=utf-8'
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

        def logado(self):
            """A sessão de quem mandou o pedido, ou None (e a resposta 401 já enviada)."""
            sessao = loja.sessao(self.token())
            if sessao is None:
                self.responder(401, {'erro': 'faça login'})
            return sessao

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
            arquivo = ROTA_ARQUIVO.match(url.path)
            if arquivo:
                return self.responder(*loja.baixar_arquivo(arquivo.group(1), url.query))
            rotas = {'/api/eu': loja.eu, '/api/meus-pedidos': loja.meus_pedidos,
                     '/api/clube/guia': loja.guia_do_clube, '/api/admin/pedidos': loja.pedidos_admin}
            pedido, nota = ROTA_PEDIDO.match(url.path), ROTA_NOTA.match(url.path)
            if url.path in rotas or pedido or nota or url.path == '/api/usuarios':
                sessao = self.logado()
                if sessao is None:
                    return
                if pedido:
                    return self.responder(*loja.ver_pedido(sessao, int(pedido.group(1))))
                if nota:
                    return self.responder(*loja.nota_do_pedido(sessao, int(nota.group(1))))
                if url.path == '/api/usuarios':
                    return self.responder(*loja.buscar_usuario(sessao, parse_qs(url.query).get('email', [''])[0]))
                return self.responder(*rotas[url.path](sessao))
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
                sessao = self.logado()
                if sessao is None:
                    return
                return self.responder(*loja.criar_pedido(sessao, json.loads(bruto or b'{}')))
            if url.path == '/webhook/pagamento':
                return self.responder(*loja.webhook_pagamento(self.headers, bruto))
            return self.responder(404, {'erro': 'rota não encontrada'})

        def do_PATCH(self):
            url = urlparse(self.path)
            bruto = self.corpo()
            if url.path == '/api/perfil':
                sessao = self.logado()
                if sessao is None:
                    return
                try:
                    corpo = json.loads(bruto or b'{}')
                except ValueError:
                    return self.responder(400, {'erro': 'corpo inválido'})
                return self.responder(*loja.atualizar_perfil(sessao, corpo))
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
