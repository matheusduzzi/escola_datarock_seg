"""Faz o que o robô fez com a newsletter da Loja Aurora: manda 50 inscrições seguidas.

Só fala com a loja no seu computador (127.0.0.1). Não aponte este script para nenhum outro
endereço: cadastro em massa num site que não é seu é ataque, mesmo "só para ver".

    python3 app.py                    # num terminal
    python3 cadastro_em_massa.py      # em outro terminal
"""
import argparse
import collections
import json
import urllib.error
import urllib.request

LIXO = ['robo{:03d}@lixo.example', 'nao-e-email-{:03d}', '<b>{:03d}</b>@lixo.example', 'x{:03d}@' + 'a' * 300 + '.example']


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--quantidade', type=int, default=50)
    args = parser.parse_args()
    respostas = collections.Counter()
    for i in range(args.quantidade):
        email = LIXO[i % len(LIXO)].format(i)
        pedido = urllib.request.Request(f'http://127.0.0.1:{args.porta}/api/newsletter',
                                        data=json.dumps({'email': email}).encode(),
                                        headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                respostas[r.status] += 1
        except urllib.error.HTTPError as erro:
            respostas[erro.code] += 1
    for status, vezes in sorted(respostas.items()):
        print(f'resposta {status}: {vezes} vezes')


if __name__ == '__main__':
    main()
