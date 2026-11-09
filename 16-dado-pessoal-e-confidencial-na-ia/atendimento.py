"""Grava o log do atendimento da Loja Aurora, com a máscara aplicada antes de escrever.

    python3 atendimento.py conversas.jsonl atendimento.log

Lê as conversas (uma por linha, em JSON) e escreve uma linha de log por conversa.
Se alguma conversa estiver com problema, não grava nada e diz qual linha.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

from mascara import mascarar

CAMPOS = ('hora', 'canal', 'cliente', 'pedido', 'mensagem', 'resposta')
CANAIS = ('whatsapp', 'formulario')


def formatar(c):
    return (f"{c['hora']} {c['canal']} {c['cliente']} {c['pedido'] or '-'}"
            f" | cliente: {mascarar(c['mensagem'])}"
            f" | assistente: {mascarar(c['resposta'])}")


def ler(caminho):
    conversas = []
    texto = caminho.read_text(encoding='utf-8-sig')
    for n, linha in enumerate(texto.splitlines(), start=1):
        if not linha.strip():
            continue
        try:
            c = json.loads(linha)
        except json.JSONDecodeError as e:
            raise ValueError(f'linha {n}: não é JSON ({e.msg})')
        if not isinstance(c, dict):
            raise ValueError(f'linha {n}: esperava um objeto com os campos {", ".join(CAMPOS)}')
        faltam = [k for k in CAMPOS if k not in c]
        if faltam:
            raise ValueError(f'linha {n}: falta o campo {", ".join(faltam)}')
        if any(not isinstance(c[k], str) for k in CAMPOS):
            raise ValueError(f'linha {n}: todos os campos são texto')
        for k in ('hora', 'cliente', 'mensagem'):
            if not c[k].strip():
                raise ValueError(f'linha {n}: o campo {k} está vazio')
        if c['canal'] not in CANAIS:
            raise ValueError(f'linha {n}: canal "{c["canal"]}" não existe (use {" ou ".join(CANAIS)})')
        if '\n' in c['mensagem'] + c['resposta']:
            c['mensagem'] = ' '.join(c['mensagem'].split())
            c['resposta'] = ' '.join(c['resposta'].split())
        conversas.append(c)
    if not conversas:
        raise ValueError('nenhuma conversa no arquivo')
    return conversas


def main(args):
    if len(args) != 2:
        print('uso: python3 atendimento.py CONVERSAS.jsonl SAIDA.log')
        return 2
    entrada, saida = Path(args[0]), Path(args[1])
    if not entrada.is_file():
        print(f'{entrada}: arquivo não encontrado')
        return 2
    if saida.resolve() == entrada.resolve():
        print('a saída não pode ser o próprio arquivo de conversas')
        return 2
    try:
        conversas = ler(entrada)
    except ValueError as e:
        print(f'{entrada}: {e}. Nada foi gravado.')
        return 2
    linhas = [formatar(c) for c in conversas]
    # Escreve num arquivo temporário e só troca no fim: ou o log sai inteiro, ou não sai.
    fd, tmp = tempfile.mkstemp(dir=saida.resolve().parent, prefix='.atendimento-')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    os.replace(tmp, saida)
    print(f'{len(linhas)} conversa(s) gravada(s) em {saida}.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
