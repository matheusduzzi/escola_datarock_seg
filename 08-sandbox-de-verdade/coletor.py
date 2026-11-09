"""O servidor de fora: faz o papel de quem recebe o que o agente manda para a internet.

Guarda cada envio em recebido/ e mostra no terminal o nome e o tamanho de cada arquivo,
nunca o conteúdo. Roda só no seu computador ou na rede do Docker do kit.

    python3 coletor.py                      # escuta em 0.0.0.0:9000
    python3 coletor.py --escuta 127.0.0.1 --porta 9000 --pasta recebido
"""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AQUI = Path(__file__).resolve().parent


class Coletor(BaseHTTPRequestHandler):
    pasta = AQUI / 'recebido'

    def log_message(self, *args):
        pass

    def do_GET(self):
        self._responder(200, 'coletor no ar\n')

    def do_POST(self):
        tamanho = int(self.headers.get('Content-Length') or 0)
        corpo = self.rfile.read(min(tamanho, 5_000_000))
        try:
            arquivos = json.loads(corpo).get('arquivos', {})
        except (ValueError, AttributeError):
            arquivos = {}
        self.pasta.mkdir(parents=True, exist_ok=True)
        n = len(list(self.pasta.glob('envio-*.json'))) + 1
        (self.pasta / f'envio-{n:03d}.json').write_bytes(corpo)
        partes = ', '.join(f'{nome} ({len(str(v).encode())} bytes)' for nome, v in arquivos.items()) or 'nada que eu entenda'
        print(f'RECEBI envio {n} em {self.path}: {partes}', flush=True)
        self._responder(200, 'recebido\n')

    def _responder(self, codigo, texto):
        dados = texto.encode()
        self.send_response(codigo)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--escuta', default='0.0.0.0')
    ap.add_argument('--porta', type=int, default=9000)
    ap.add_argument('--pasta', default=os.environ.get('COLETOR_PASTA', '/recebido' if Path('/recebido').is_dir() else str(AQUI / 'recebido')))
    a = ap.parse_args()
    Coletor.pasta = Path(a.pasta)
    servidor = ThreadingHTTPServer((a.escuta, a.porta), Coletor)
    print(f'Coletor em {a.escuta}:{a.porta}, guardando em {Coletor.pasta}', flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
