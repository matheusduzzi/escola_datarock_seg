"""Procura num log o dado pessoal que sobrou: e-mail e sequências de números com cara de CPF, telefone ou cartão.

    python3 procurar.py atendimento.log

Não usa as regras do mascara.py: procura de um jeito mais largo, para pegar o que a máscara deixou passar.
Mostra só os dois últimos dígitos do que achou. Sai com 0 quando não sobra nada, 1 quando sobra e 2 quando
não consegue ler o arquivo.
"""
import re
import sys
from pathlib import Path

EMAIL = re.compile(r'[^\s|]*@[\w-]+(?:\.[\w-]+)+')
NUMERO = re.compile(r'(?<![\w])\+?\(?\d(?:[\d().\s-]*\d)?')
MARCADORES = ('[CPF]', '[TELEFONE]', '[EMAIL]', '[CARTAO]')


def tipo(digitos):
    n = len(digitos)
    if n < 8:
        return None
    if n <= 10:
        return 'telefone'
    if n == 11:
        return 'CPF ou celular'
    if n <= 13:
        return 'telefone com +55'
    if n <= 19:
        return 'cartão'
    return 'número longo'


def esconder(trecho):
    total = sum(ch.isdigit() for ch in trecho)
    vistos, saida = 0, []
    for ch in trecho:
        if ch.isdigit():
            vistos += 1
            saida.append(ch if vistos > total - 2 else '•')
        else:
            saida.append(ch)
    return ''.join(saida)


def achados(linha):
    for m in EMAIL.finditer(linha):
        dominio = m.group(0).split('@', 1)[1]
        yield 'e-mail', '•••@' + dominio
    sem_email = EMAIL.sub(' ', linha)
    for m in NUMERO.finditer(sem_email):
        t = tipo(re.sub(r'\D', '', m.group(0)))
        if t:
            yield t, esconder(m.group(0).strip())


def main(args):
    if len(args) != 1:
        print('uso: python3 procurar.py ARQUIVO.log')
        return 2
    caminho = Path(args[0])
    if not caminho.is_file():
        print(f'{caminho}: arquivo não encontrado')
        return 2
    linhas = caminho.read_text(encoding='utf-8-sig').splitlines()
    if not any(l.strip() for l in linhas):
        print(f'{caminho}: arquivo vazio, nada para procurar')
        return 2
    contagem = {}
    print(f'{caminho.name}: {len(linhas)} linha(s)')
    for n, linha in enumerate(linhas, start=1):
        for t, visto in achados(linha):
            contagem[t] = contagem.get(t, 0) + 1
            print(f'  linha {n}: {t} ({visto})')
    texto = '\n'.join(linhas)
    print('Marcadores: ' + ', '.join(f'{m} {texto.count(m)}' for m in MARCADORES))
    if contagem:
        print('Sobrou dado pessoal: ' + ', '.join(f'{v} {k}' for k, v in sorted(contagem.items())) + '.')
        return 1
    print('Nenhum e-mail, CPF, telefone ou cartão sobrando.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
