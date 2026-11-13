"""Loja Aurora: o app como ficou depois das aulas de autenticação, IDOR e webhook.

Login pelo provedor, regra de preço e de plano no servidor, cada pedido visível só para o dono,
busca pela lista do que é aceito, webhook assinado, limite na newsletter e no assistente.
Continua sendo um app de treino, só em 127.0.0.1. Não publique este app.

    python3 app.py            # sobe em http://127.0.0.1:8765
    python3 app.py --porta 9000
"""
import argparse
import hashlib
import hmac
import json
import re
import secrets
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
from limitador import Limitador  # noqa: E402

HOST = '127.0.0.1'
DESCONTO_CLUBE_PCT = 10
# CORS diz ao NAVEGADOR de quem ele pode ler a resposta. Não segura curl, script nem robô:
# quem protege a API é a assinatura, o login e o limite, logo abaixo.
ORIGEM_DO_SITE = 'https://loja-aurora.example'

# Lista do que é aceito. O que não está aqui leva 400.
ORDENS = {'id': 'id', 'nome': 'nome', 'preco_centavos': 'preco_centavos'}   # nome de coluna não vai em "?"
LIMITE_MAXIMO = 20          # linhas por resposta da busca
BUSCA_MAXIMO = 60           # caracteres no texto da busca
PERGUNTA_MAXIMO = 500       # caracteres na pergunta ao assistente
EMAIL = re.compile(r'[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]{1,63}(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,24}')
STATUS_DO_GATEWAY = {'pago', 'estornado', 'cancelado'}


class Invalido(Exception):
    """Pedido com dado fora da lista do que é aceito: vira 400 com uma mensagem curta."""


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
        self.limite_newsletter = Limitador(maximo=5, janela_segundos=600)   # por IP
        self.limite_assistente = Limitador(maximo=5, janela_segundos=60)    # por cliente
        with self.conectar() as con:
            con.execute('create table if not exists eventos_processados (evento_id text primary key, recebido_em text)')

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

    def buscar_produtos(self, busca, ordem='id', limite=str(LIMITE_MAXIMO)):
        if len(busca) > BUSCA_MAXIMO:
            raise Invalido(f'a busca aceita até {BUSCA_MAXIMO} caracteres')
        if ordem not in ORDENS:
            raise Invalido('ordem aceita: ' + ', '.join(ORDENS))
        if not re.fullmatch(r'[0-9]{1,3}', limite) or not 1 <= int(limite) <= LIMITE_MAXIMO:
            raise Invalido(f'limite aceita um número de 1 a {LIMITE_MAXIMO}')
        # O texto da busca e o limite vão como dado, nos "?". A coluna da ordem sai da lista acima.
        sql = ('select id, nome, categoria, preco_centavos from produtos where nome like ?'
               ' order by ' + ORDENS[ordem] + ' limit ?')
        with self.conectar() as con:
            return [dict(l) for l in con.execute(sql, ('%' + busca + '%', int(limite))).fetchall()]

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
                'insert into pedidos (cliente_id, produto_id, quantidade, desconto_centavos, credito_centavos, total_centavos,'
                ' status, criado_em) values (?, ?, ?, ?, ?, ?, ?, ?)',
                (sessao['id'], produto_id, quantidade, desconto, credito, total, 'aguardando pagamento', agora()))
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
        liberado, espera = self.limite_newsletter.permitir(ip)
        if not liberado:
            return 429, {'erro': 'muitas inscrições seguidas; tente mais tarde'}, {'Retry-After': str(espera)}
        email = corpo.get('email')
        if not isinstance(email, str) or len(email) > 254 or not EMAIL.fullmatch(email):
            return 400, {'erro': 'e-mail inválido'}
        with self.conectar() as con:
            con.execute('insert into newsletter (email, ip, criado_em) values (?, ?, ?)', (email, ip, agora()))
        return 201, {'mensagem': 'inscrição recebida'}

    def assistente(self, sessao, corpo):
        # Cada chamada ao modelo entra na conta da loja: login, tamanho e limite vêm ANTES dela.
        if not sessao:
            return 401, {'erro': 'faça login'}
        pergunta = corpo.get('pergunta')
        if not isinstance(pergunta, str) or not 1 <= len(pergunta.strip()) <= PERGUNTA_MAXIMO:
            return 400, {'erro': f'a pergunta precisa ter de 1 a {PERGUNTA_MAXIMO} caracteres'}
        liberado, espera = self.limite_assistente.permitir(sessao['id'])
        if not liberado:
            return 429, {'erro': 'muitas perguntas seguidas; espere um pouco'}, {'Retry-After': str(espera)}
        return 200, {'resposta': self.modelo.responder(pergunta, sessao['id'])}

    # Webhooks --------------------------------------------------------------------------------

    def webhook_pagamento(self, cabecalhos, bruto):
        # 1. A assinatura, antes de ler o corpo: HMAC do corpo exato com o segredo combinado com o gateway.
        segredo = self.env.get('WEBHOOK_SEGREDO', '').encode()
        esperado = hmac.new(segredo, bruto, hashlib.sha256).hexdigest()
        if not segredo or not hmac.compare_digest(esperado, cabecalhos.get('X-Aurora-Assinatura', '')):
            return 401, {'erro': 'assinatura inválida'}
        # 2. O formato, pela lista do que é aceito.
        try:
            corpo = json.loads(bruto)
        except ValueError:
            return 400, {'erro': 'corpo inválido'}
        if not isinstance(corpo, dict) or not isinstance(corpo.get('pedido_id'), int) \
                or corpo.get('status', 'pago') not in STATUS_DO_GATEWAY:
            return 400, {'erro': 'evento inválido'}
        # 3. O evento repetido: o id de cada evento aplicado fica guardado. Sem evento_id, o corpo assinado é a chave.
        chave = str(corpo.get('evento_id') or hashlib.sha256(bruto).hexdigest())
        with self.conectar() as con:
            try:
                con.execute('insert into eventos_processados (evento_id, recebido_em) values (?, ?)', (chave, agora()))
            except sqlite3.IntegrityError:
                return 200, {'ok': True, 'repetido': True}   # 200 para o gateway parar de reenviar; nada muda
            mudou = con.execute('update pedidos set status = ? where id = ?', (corpo.get('status', 'pago'), corpo['pedido_id']))
            if mudou.rowcount != 1:
                con.rollback()
                return 404, {'erro': 'pedido não encontrado'}
        return 200, {'ok': True}

    # O webhook do PagaFácil saiu: a loja não usa mais esse gateway. Rota que ninguém chama
    # é porta aberta que ninguém vigia. O inventário dos endpoints está no relatório.


def objeto(bruto):
    corpo = json.loads(bruto or b'{}')
    if not isinstance(corpo, dict):
        raise Invalido('o corpo precisa ser um objeto JSON')
    return corpo


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

        def tratar(self, rotas):
            try:
                rotas()
            except Invalido as erro:
                self.responder(400, {'erro': str(erro)})
            except ValueError:   # JSON quebrado, número que não é número
                self.responder(400, {'erro': 'pedido inválido'})
            except Exception:
                # O detalhe fica no log do servidor, com um código. O cliente recebe só o código.
                codigo = secrets.token_hex(4)
                self.log_message('erro %s em %s %s\n%s', codigo, self.command, self.path, traceback.format_exc())
                self.responder(500, {'erro': 'erro interno', 'codigo': codigo})

        def do_GET(self):
            self.tratar(self.rotas_get)

        def do_POST(self):
            self.tratar(self.rotas_post)

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
                limite = consulta.get('limite', [str(LIMITE_MAXIMO)])[0]
                return self.responder(200, {'produtos': loja.buscar_produtos(busca, ordem, limite)})
            if url.path == '/api/eu':
                return self.responder(*loja.eu(loja.sessao(self.token())))
            if url.path.startswith('/api/pedidos/'):
                numero = url.path.rsplit('/', 1)[1]
                if not re.fullmatch(r'[0-9]{1,9}', numero):
                    return self.responder(404, {'erro': 'pedido não encontrado'})
                return self.responder(*loja.ver_pedido(loja.sessao(self.token()), int(numero)))
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
                return self.responder(*loja.inscrever_newsletter(objeto(bruto), self.client_address[0]))
            if url.path == '/api/assistente':
                return self.responder(*loja.assistente(loja.sessao(self.token()), objeto(bruto)))
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
