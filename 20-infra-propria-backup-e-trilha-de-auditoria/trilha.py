"""A trilha do que o agente fez: uma linha por ação, cada linha presa à anterior.

    python3 trilha.py ver                     # lê a trilha
    python3 trilha.py verificar               # vê se alguma linha mudou ou sumiu
    python3 trilha.py ancora                  # a linha para guardar fora do servidor
    python3 trilha.py verificar --ancora "6 5c1f…"

Cada linha é um JSON com o número, a hora, o agente, a ação, o detalhe, o resultado,
o hash da linha anterior e o hash dela mesma (sha256). Mudar uma linha quebra o hash
dela. Apagar uma linha do meio quebra a contagem e a ligação com a anterior.

O que a corrente não pega sozinha: apagar as últimas linhas, ou refazer a trilha inteira
com hashes novos. Para isso serve a âncora: o número e o hash da última linha, guardados
num lugar que o agente não alcança. A verificação com a âncora pega as duas coisas.

Quem escreve a trilha é a camada de ferramentas, não o modelo. Num servidor de verdade,
a trilha também vai para fora do alcance do agente (outro usuário, outra máquina).
Por padrão usa trilha/agente-noturno.jsonl; passe outro arquivo com --arquivo.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from relogio import agora

PADRAO = Path('trilha/agente-noturno.jsonl')
ZERO = '0' * 64
CAMPOS = ('n', 'hora', 'agente', 'acao', 'detalhe', 'resultado', 'anterior')


def hash_da(linha):
    corpo = {c: linha[c] for c in CAMPOS}
    return hashlib.sha256(json.dumps(corpo, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def ler(caminho):
    if not caminho.exists():
        return []
    return caminho.read_text(encoding='utf-8').splitlines()


class Trilha:
    def __init__(self, caminho=PADRAO):
        self.caminho = Path(caminho)

    def anotar(self, agente, acao, detalhe, resultado):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        linhas = ler(self.caminho)
        ultima = json.loads(linhas[-1]) if linhas else {'n': 0, 'hash': ZERO}
        linha = {'n': ultima['n'] + 1, 'hora': agora().isoformat(), 'agente': agente, 'acao': acao,
                 'detalhe': detalhe, 'resultado': resultado, 'anterior': ultima['hash']}
        linha['hash'] = hash_da(linha)
        with open(self.caminho, 'a', encoding='utf-8') as f:
            f.write(json.dumps(linha, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        return linha


def ver(caminho):
    linhas = ler(caminho)
    if not linhas:
        print(f'{caminho.as_posix()} está vazia ou não existe.')
        return 2
    for texto in linhas:
        try:
            l = json.loads(texto)
            print(f'{l["n"]:>2}  {l["hora"][:19].replace("T", " ")}  {l["agente"]}  {l["acao"]:<14} {l["detalhe"]} → {l["resultado"]}')
        except (ValueError, KeyError):
            print(f'??  linha que não dá para ler: {texto[:60]}')
    return 0


def verificar(caminho, ancora=None):
    linhas = ler(caminho)
    print(f'Trilha: {caminho.as_posix()}, {len(linhas)} linhas')
    problemas = []
    if not linhas:
        problemas.append('VAZIA    a trilha não tem nenhuma linha (ou o arquivo sumiu)')
    anterior, esperado, ultima = ZERO, 1, None
    for i, texto in enumerate(linhas, start=1):
        try:
            l = json.loads(texto)
            n = int(l['n'])
            [l[c] for c in CAMPOS + ('hash',)]
        except (ValueError, KeyError, TypeError):
            problemas.append(f'ILEGÍVEL linha {i} do arquivo: não é uma linha da trilha')
            anterior, esperado = None, None
            continue
        if esperado is not None and n > esperado:
            faixa = str(esperado) if n == esperado + 1 else f'{esperado} a {n - 1}'
            problemas.append(f'SUMIU    linha {faixa}: depois da {esperado - 1} vem a {n}')
        elif esperado is not None and n < esperado:
            problemas.append(f'FORA     linha {n}: aparece depois da {esperado - 1}')
        elif anterior is not None and l['anterior'] != anterior:
            problemas.append(f'QUEBRADA linha {n}: não aponta para a linha anterior')
        if hash_da(l) != l['hash']:
            problemas.append(f'ALTERADA linha {n}: o conteúdo não bate com o hash anotado')
        anterior, esperado, ultima = l['hash'], n + 1, l
    if not problemas and linhas:
        print(f'ok       linhas 1 a {len(linhas)}: cada uma bate com o próprio hash e aponta para a anterior')
    for p in problemas:
        print(p)
    if ancora:
        try:
            num, h = ancora.split()
            num = int(num)
        except ValueError:
            print('A âncora tem o formato "número hash", como sai do: python3 trilha.py ancora')
            return 2
        alvo = None
        for texto in linhas:
            try:
                l = json.loads(texto)
            except ValueError:
                continue
            if l.get('n') == num:
                alvo = l
        if alvo is None:
            ate = ultima['n'] if ultima else 0
            problemas.append(f'SUMIU    linhas depois da {ate}: a âncora diz que a trilha ia até a {num}')
            print(problemas[-1])
        elif alvo.get('hash') != h:
            problemas.append(f'REFEITA  linha {num}: não é a mesma que a âncora guardou')
            print(problemas[-1])
        else:
            print(f'ok       âncora: a linha {num} é a mesma que ficou guardada fora')
    else:
        print('Âncora: não informada. Sem ela, apagar as últimas linhas ou refazer a trilha não aparece.')
    print('RESULTADO:', 'TRILHA ALTERADA' if problemas else 'TRILHA ÍNTEGRA')
    return 1 if problemas else 0


def ancora(caminho):
    linhas = ler(caminho)
    if not linhas:
        print(f'{caminho.as_posix()} está vazia ou não existe.')
        return 2
    l = json.loads(linhas[-1])
    print(f'{l["n"]} {l["hash"]}')
    return 0


def main():
    p = argparse.ArgumentParser(description='Lê e verifica a trilha do agente.')
    p.add_argument('modo', choices=['ver', 'verificar', 'ancora'])
    p.add_argument('--arquivo', default=str(PADRAO))
    p.add_argument('--ancora', help='"número hash", como sai do modo ancora')
    a = p.parse_args()
    caminho = Path(a.arquivo)
    if a.modo == 'ver':
        return ver(caminho)
    if a.modo == 'ancora':
        return ancora(caminho)
    return verificar(caminho, a.ancora)


if __name__ == '__main__':
    sys.exit(main())
