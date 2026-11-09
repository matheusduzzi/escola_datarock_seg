"""Registro local do curso: responde como o registro do npm, só para os pacotes da pasta registro/.

    python3 registro.py                 # escuta em http://127.0.0.1:4873 até Ctrl+C
    python3 registro.py --porta 4874    # outra porta

Num segundo terminal:

    npm view minimist-safe --registry http://127.0.0.1:4873
    npm view minimist-safe scripts repository.url --registry http://127.0.0.1:4873

Os pacotes daqui não têm código. O pedido do arquivo do pacote (o .tgz) recebe 410 e nada se instala.
O registro escuta só no seu computador (127.0.0.1). As datas são contadas a partir de agora,
para o pacote parecer sempre recém-publicado, como na aula.

Saída: 0 quando você para com Ctrl+C; 2 quando a porta está ocupada.
"""
import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

PASTA = Path(__file__).resolve().parent / 'registro'
NOME = re.compile(r'^[a-z0-9][a-z0-9._-]{0,213}$')
AVISO_TGZ = ('Este pacote só existe no registro do curso. Ele não tem código e não se instala.\n').encode()


def quando(valor, agora):
    """'-3d' vira a data de 3 dias atrás; uma data pronta fica como está."""
    m = re.fullmatch(r'-(\d+)d', valor)
    if not m:
        return valor
    return (agora - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def documento(nome, base):
    arquivo = PASTA / f'{nome}.json'
    if not NOME.match(nome) or not arquivo.is_file():
        return None
    d = json.loads(arquivo.read_text(encoding='utf-8'))
    agora = datetime.now(timezone.utc)
    d['time'] = {k: quando(v, agora) for k, v in d.get('time', {}).items()}
    for versao, m in d['versions'].items():
        arquivo_tgz = f'{nome}-{versao}.tgz'
        m['dist'] = {
            'tarball': f'{base}/{nome}/-/{arquivo_tgz}',
            'shasum': hashlib.sha1(AVISO_TGZ).hexdigest(),
            'integrity': 'sha512-' + base64.b64encode(hashlib.sha512(AVISO_TGZ).digest()).decode(),
        }
    return d


class Registro(BaseHTTPRequestHandler):
    server_version = 'registro-do-curso'

    def log_message(self, formato, *args):
        sys.stdout.write('%s %s\n' % (self.command, self.path))
        sys.stdout.flush()

    def responder(self, codigo, corpo, tipo='application/json'):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header('Content-Type', tipo + '; charset=utf-8')
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        caminho = unquote(urlsplit(self.path).path).strip('/')
        partes = caminho.split('/')
        base = 'http://' + (self.headers.get('Host') or '127.0.0.1')
        if len(partes) == 3 and partes[1] == '-' and partes[2].endswith('.tgz'):
            self.responder(410, AVISO_TGZ, 'text/plain')
            return
        d = documento(partes[0], base) if len(partes) == 1 else None
        if d is None:
            self.responder(404, {'error': 'Not found'})
            return
        self.responder(200, d)

    def do_PUT(self):
        self.responder(405, {'error': 'o registro do curso não aceita publicação'})

    do_POST = do_DELETE = do_PUT


def main():
    p = argparse.ArgumentParser(description='Registro local do curso (só leitura).')
    p.add_argument('--porta', type=int, default=4873)
    a = p.parse_args()
    try:
        servidor = ThreadingHTTPServer(('127.0.0.1', a.porta), Registro)
    except OSError as e:
        print(f'não consegui abrir a porta {a.porta}: {e}. Tente outra com --porta.', file=sys.stderr)
        return 2
    print(f'registro do curso em http://127.0.0.1:{a.porta} (Ctrl+C para parar)', flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
