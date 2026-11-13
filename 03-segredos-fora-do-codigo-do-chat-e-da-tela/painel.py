"""O painel de chaves dos provedores da Loja Aurora (gateway de pagamento, mapa e provedor de IA).

Faz o papel da página de chaves do provedor: listar, revogar e criar. Guarda tudo em painel.json.

    python3 painel.py listar
    python3 painel.py revogar --final W3qT
    python3 painel.py nova --provedor gateway --gravar repo-aurora/.env --variavel PAGAMENTO_CHAVE_SECRETA

A chave nova vai direto para o arquivo .env. Ela nunca aparece na tela: só os 4 últimos caracteres.
"""
import argparse
import hashlib
import json
import string
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PREFIXOS = {'gateway': 'aurora_sk_live_', 'ia': 'aurora_llm_sk_'}
NOMES = {'gateway': 'gateway de pagamento', 'ia': 'provedor de IA'}


def mascarar(chave):
    return chave[:chave.rfind('_') + 1] + '…' + chave[-4:]


def carregar(caminho):
    if not caminho.exists():
        sys.exit('Não achei painel.json. Rode python3 montar.py antes.')
    return json.loads(caminho.read_text(encoding='utf-8'))


def salvar(caminho, painel):
    caminho.write_text(json.dumps(painel, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def listar(painel, _args):
    print(f'{"provedor":9} {"tipo":8} {"chave":24} {"criada":11} estado')
    for c in painel['chaves']:
        estado = c['estado'] + (f' em {c["revogada_em"]}' if c.get('revogada_em') else '')
        print(f'{c["provedor"]:9} {c["tipo"]:8} {mascarar(c["valor"]):24} {c["criada"]:11} {estado}')
    return 0


def revogar(painel, args):
    alvo = [c for c in painel['chaves'] if c['valor'].endswith(args.final)]
    if len(alvo) != 1:
        print(f'{len(alvo)} chaves terminam em {args.final}. Use os 4 últimos caracteres de uma chave só.')
        return 1
    chave = alvo[0]
    if chave['estado'] == 'revogada':
        print(f'{mascarar(chave["valor"])} já estava revogada.')
        return 0
    chave['estado'], chave['revogada_em'] = 'revogada', date.today().isoformat()
    print(f'Revogada: {mascarar(chave["valor"])} ({chave["provedor"]}). Quem tiver uma cópia dela não consegue mais usar.')
    return 0


def nova(painel, args):
    destino = Path(args.gravar)
    if not destino.parent.is_dir():
        print(f'A pasta de {destino} não existe.')
        return 1
    # A chave nasce do estado do painel: cada pedido gera uma diferente.
    base = hashlib.sha256((json.dumps(painel, sort_keys=True) + args.provedor).encode()).digest()
    letras = string.ascii_letters + string.digits
    valor = PREFIXOS[args.provedor] + ''.join(letras[b % len(letras)] for b in base[:24])
    painel['chaves'].append({'provedor': args.provedor, 'tipo': 'secreta', 'valor': valor,
                             'criada': date.today().isoformat(), 'estado': 'ativa'})
    linhas = destino.read_text(encoding='utf-8').splitlines() if destino.exists() else []
    linhas = [l for l in linhas if not l.strip().startswith(args.variavel + '=')] + [f'{args.variavel}={valor}']
    destino.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    print(f'Chave nova do {NOMES[args.provedor]} gravada em {destino} como {args.variavel} (final {valor[-4:]}).')
    return 0


def main():
    parser = argparse.ArgumentParser(description='Painel de chaves dos provedores da Loja Aurora.')
    parser.add_argument('--painel', default=str(AQUI / 'painel.json'))
    sub = parser.add_subparsers(dest='acao', required=True)
    sub.add_parser('listar', help='mostra as chaves, mascaradas')
    r = sub.add_parser('revogar', help='revoga a chave que termina com os 4 caracteres')
    r.add_argument('--final', required=True)
    n = sub.add_parser('nova', help='cria chave secreta e grava no .env, sem mostrar')
    n.add_argument('--provedor', choices=sorted(PREFIXOS), required=True)
    n.add_argument('--gravar', required=True, help='o arquivo .env que recebe a chave')
    n.add_argument('--variavel', required=True, help='o nome da variável no .env')
    args = parser.parse_args()
    caminho = Path(args.painel)
    painel = carregar(caminho)
    codigo = {'listar': listar, 'revogar': revogar, 'nova': nova}[args.acao](painel, args)
    if args.acao != 'listar' and codigo == 0:
        salvar(caminho, painel)
    return codigo


if __name__ == '__main__':
    sys.exit(main())
