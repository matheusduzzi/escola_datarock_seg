"""Lê o desenho dos cofres em CSV e mostra o que cada um alcança e o que cai se algo vazar.

    python3 alcance.py atalho.csv
    python3 alcance.py meu-cofre.csv

Sai com 0 quando não acha problema e com 1 quando acha. Só lê o arquivo; não abre
gerenciador de senhas nenhum nem chama a rede.
"""
import csv
import re
import sys
from pathlib import Path

COLUNAS = ['cofre', 'dono', 'quem_acessa', 'item', 'tipo', 'de_quem', 'limite', 'alcance']
OBRIGATORIAS = ['cofre', 'dono', 'quem_acessa', 'item', 'tipo', 'de_quem', 'alcance']
TIPOS = {'senha', 'chave', 'token', 'cartao', 'cartao-virtual', 'nota'}
VAGOS = {'equipe', 'todos', 'time', 'loja', 'empresa', 'ninguém', 'ninguem', 'não sei', 'nao sei', '?'}
# Valor de segredo ou número de cartão colado no desenho: o desenho circula, o valor nunca entra.
PARECE_SEGREDO = re.compile(r'(sk|pk|rk)[-_][A-Za-z0-9_]{6,}|ghp_|github_pat_|ops_ey|xox[bp]-|[A-Za-z0-9+/_-]{28,}')
PARECE_CARTAO = re.compile(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)')


def agente(nome):
    return nome.startswith('agente:')


def lista(texto):
    return [p.strip() for p in texto.split(';') if p.strip()]


def ler(caminho):
    with open(caminho, newline='', encoding='utf-8-sig') as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor, None)
        if cabecalho is None:
            raise ValueError('o arquivo está vazio')
        if [c.strip() for c in cabecalho] != COLUNAS:
            raise ValueError('o cabeçalho precisa ser: ' + ','.join(COLUNAS))
        linhas = []
        for n, campos in enumerate(leitor, start=2):
            if not any(c.strip() for c in campos):
                continue
            if len(campos) != len(COLUNAS):
                raise ValueError(f'linha {n}: {len(campos)} campos, o cabeçalho tem {len(COLUNAS)} (texto com vírgula vai entre aspas)')
            linhas.append((n, {c: v.strip() for c, v in zip(COLUNAS, campos)}))
    if not linhas:
        raise ValueError('o desenho não tem nenhum item')
    return linhas


def analisar(linhas):
    problemas = []
    for n, l in linhas:
        for c in OBRIGATORIAS:
            if not l[c]:
                problemas.append(f'linha {n}: a coluna {c} está vazia')
        if l['tipo'] and l['tipo'] not in TIPOS:
            problemas.append(f'linha {n}: tipo «{l["tipo"]}» não existe; use ' + ', '.join(sorted(TIPOS)))
        for c in COLUNAS:
            if PARECE_SEGREDO.search(l[c]) or PARECE_CARTAO.search(l[c]):
                problemas.append(f'linha {n}: a coluna {c} parece ter o valor de uma senha, chave ou cartão; o desenho leva só o nome')
                break

    cofres = {}
    for n, l in linhas:
        c = cofres.setdefault(l['cofre'], {'linha': n, 'dono': l['dono'], 'quem': [], 'itens': []})
        c['itens'].append((n, l))
        for q in lista(l['quem_acessa']):
            if q not in c['quem']:
                c['quem'].append(q)
        if l['dono'] and l['dono'] != c['dono']:
            problemas.append(f'linha {n}: o cofre {l["cofre"]} aparece com dois donos ({c["dono"]} e {l["dono"]})')

    for nome, c in cofres.items():
        dono = c['dono']
        if dono and (dono.lower() in VAGOS or agente(dono) or ';' in dono):
            problemas.append(f'cofre {nome}: o dono é «{dono}»; o dono é uma pessoa, com nome, que responde pelo cofre')
        agentes = [q for q in c['quem'] if agente(q)]
        if agentes and len(c['quem']) > 1:
            outros = ', '.join(q for q in c['quem'] if q != agentes[0])
            problemas.append(f'cofre {nome}: {agentes[0]} divide o cofre com {outros}; o cofre de um agente é só dele')
        for n, l in c['itens']:
            for a in agentes:
                if l['tipo'] == 'cartao':
                    problemas.append(f'linha {n}, {l["item"]}: meio de pagamento num cofre que {a} acessa; se o pagamento for inevitável, use um cartão virtual só dele, com o menor limite da tarefa')
                elif l['de_quem'] and l['de_quem'] != a:
                    problemas.append(f'linha {n}, {l["item"]}: {a} entra com uma conta que não é dele (conta de: {l["de_quem"]}); dê ao agente a conta dele')
            if l['tipo'] == 'cartao-virtual' and not l['limite']:
                problemas.append(f'linha {n}, {l["item"]}: cartão virtual sem limite; anote o menor limite que a tarefa pede')

    vistos = {}
    for n, l in linhas:
        if l['item'] in vistos and vistos[l['item']][1] != l['cofre']:
            problemas.append(f'linha {n}, {l["item"]}: o mesmo item está também no cofre {vistos[l["item"]][1]} (linha {vistos[l["item"]][0]}); quando ele mudar num cofre, a cópia do outro fica velha')
        vistos.setdefault(l['item'], (n, l['cofre']))
    return cofres, problemas


def abre_do_item(l):
    # O limite do cartão faz parte do que ele abre: «pagar etiqueta de frete (limite R$ 250 por dia)».
    sufixo = f' (limite {l["limite"]})' if l['limite'] else ''
    return [a + sufixo for a in lista(l['alcance'])]


def juntar(itens):
    abre = []
    for _, l in itens:
        for a in abre_do_item(l):
            if a not in abre:
                abre.append(a)
    return sorted(abre, key=str.lower)


def mostrar(caminho, linhas, cofres, problemas):
    pessoas = []
    for c in cofres.values():
        for q in c['quem']:
            if q not in pessoas:
                pessoas.append(q)
    print(f'{Path(caminho).name}: {len(cofres)} cofre(s), {len(linhas)} item(ns), {len(pessoas)} com acesso')
    print('\nQuem alcança o quê:')
    grupos = {}
    for q in sorted(pessoas, key=lambda p: (not agente(p), p.lower())):
        seus = tuple(nome for nome, c in cofres.items() if q in c['quem'])
        grupos.setdefault(seus, []).append(q)
    for seus, quem in grupos.items():
        itens = [i for nome in seus for i in cofres[nome]['itens']]
        abre = juntar(itens)
        print(f'  {", ".join(quem)}: {len(itens)} item(ns) em {len(seus)} cofre(s); abre {len(abre)}: ' + ', '.join(abre))
    print('\nSe um cofre vazar, cai:')
    for nome, c in sorted(cofres.items(), key=lambda kv: (-len(juntar(kv[1]['itens'])), kv[0].lower())):
        abre = juntar(c['itens'])
        print(f'  {nome} (dono {c["dono"]}; acessa: {", ".join(c["quem"])}): {len(abre)}')
    print('\nSe uma credencial vazar, cai:')
    por_item = sorted(linhas, key=lambda nl: (-len(lista(nl[1]['alcance'])), nl[0]))
    for n, l in por_item:
        print(f'  {l["item"]}: ' + ', '.join(abre_do_item(l)))
    if problemas:
        print('\nProblemas:')
        for p in problemas:
            print('  - ' + p)
    print(f'\nResumo: {len(problemas)} problema(s).' if problemas else '\nResumo: nenhum problema.')


def main(argv):
    if len(argv) != 2 or argv[1].startswith('-'):
        print('uso: python3 alcance.py ARQUIVO.csv', file=sys.stderr)
        return 2
    caminho = argv[1]
    if not Path(caminho).is_file():
        print(f'{caminho}: arquivo não encontrado', file=sys.stderr)
        return 2
    try:
        linhas = ler(caminho)
    except (ValueError, UnicodeDecodeError, csv.Error) as e:
        print(f'{Path(caminho).name}: {e}', file=sys.stderr)
        return 2
    cofres, problemas = analisar(linhas)
    mostrar(caminho, linhas, cofres, problemas)
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
