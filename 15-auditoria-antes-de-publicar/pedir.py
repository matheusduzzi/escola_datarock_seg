"""Manda um pedido para a Loja Aurora que está rodando, entrando com uma conta de teste.

    python3 pedir.py caio /api/clube/guia
    python3 pedir.py caio "/api/admin/vendas?dia=2026-11-27"
    python3 pedir.py ninguem /api/admin/pedidos         # sem login

Serve para os testes à mão da checklist: entra com a conta (bia, caio, duda, renata ou ninguem),
faz o pedido GET e mostra o código e a resposta. A loja precisa estar aberta em outro terminal,
com python3 app.py dentro de repo-aurora. Só fala com 127.0.0.1.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

CONTAS = {
    'bia': ('bia@cliente.example', 'Bia#teste1'),
    'caio': ('caio@cliente.example', 'Caio#teste2'),
    'duda': ('duda@cliente.example', 'Duda#teste3'),
    'renata': ('renata@aurora.example', 'Renata#teste4'),
}


def pedir(base, metodo, caminho, corpo=None, token=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(base + caminho, data=dados, method=metodo)
    pedido.add_header('Content-Type', 'application/json')
    if token:
        pedido.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(pedido, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read().decode()


def main():
    parser = argparse.ArgumentParser(description='Pedido GET para a Loja Aurora aberta em 127.0.0.1.')
    parser.add_argument('conta', choices=[*CONTAS, 'ninguem'])
    parser.add_argument('caminho', help='por exemplo /api/clube/guia')
    parser.add_argument('--porta', type=int, default=8765)
    args = parser.parse_args()
    base = f'http://127.0.0.1:{args.porta}'
    token = None
    try:
        if args.conta != 'ninguem':
            email, senha = CONTAS[args.conta]
            status, texto = pedir(base, 'POST', '/api/login', {'email': email, 'senha': senha})
            if status != 200:
                sys.exit(f'o login de {args.conta} respondeu {status}: {texto}')
            token = json.loads(texto)['token']
        status, texto = pedir(base, 'GET', args.caminho, token=token)
    except urllib.error.URLError:
        sys.exit(f'a loja não está aberta em {base}. Em outro terminal: cd repo-aurora && python3 app.py')
    print(status, texto)
    return 0


if __name__ == '__main__':
    sys.exit(main())
