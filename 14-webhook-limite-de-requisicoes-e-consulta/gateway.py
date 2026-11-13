"""O gateway de pagamento da Loja Aurora. Não edite este arquivo.

Faz o papel do gateway de verdade: quando um pagamento muda, ele manda um evento para o webhook
da loja, em /webhook/pagamento. Cada evento tem um evento_id único e vai assinado com o
WEBHOOK_SEGREDO combinado com a loja: a assinatura é um HMAC-SHA256 do corpo exato do pedido,
em hexadecimal, no cabeçalho X-Aurora-Assinatura.

Se a loja não responder com 2xx, o gateway manda o MESMO evento de novo, com o mesmo corpo e a
mesma assinatura. Por isso a loja pode receber o mesmo evento mais de uma vez.

    python3 gateway.py 4 pago                # manda "pedido 4 pago" para a loja em 127.0.0.1:8765
    python3 gateway.py 4 estornado --porta 9000
"""
import argparse
import hashlib
import hmac
import json
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

CABECALHO = 'X-Aurora-Assinatura'


def assinar(segredo, bruto):
    return hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()


def evento(segredo, pedido_id, status, evento_id=None):
    """Monta um evento como o gateway monta. Retorna (corpo em bytes, cabeçalhos)."""
    corpo = {'evento_id': evento_id or 'evt_' + secrets.token_hex(8), 'tipo': 'pagamento.atualizado',
             'pedido_id': pedido_id, 'status': status}
    bruto = json.dumps(corpo).encode()
    return bruto, {'Content-Type': 'application/json', CABECALHO: assinar(segredo, bruto)}


def main():
    parser = argparse.ArgumentParser(description='Manda um evento de pagamento para a Loja Aurora em 127.0.0.1.')
    parser.add_argument('pedido_id', type=int)
    parser.add_argument('status', choices=['pago', 'estornado', 'cancelado'])
    parser.add_argument('--porta', type=int, default=8765)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app import ler_env
    bruto, cabecalhos = evento(ler_env()['WEBHOOK_SEGREDO'], args.pedido_id, args.status)
    pedido = urllib.request.Request(f'http://127.0.0.1:{args.porta}/webhook/pagamento', data=bruto,
                                    headers=cabecalhos, method='POST')
    try:
        with urllib.request.urlopen(pedido, timeout=10) as r:
            print(r.status, r.read().decode())
    except urllib.error.HTTPError as erro:
        print(erro.code, erro.read().decode())


if __name__ == '__main__':
    main()
