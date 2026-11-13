"""Análise do código parado (SAST): procura padrões de falha nos arquivos .py de uma pasta.

    python3 sast.py PASTA

Faz o papel de um SAST como o Semgrep, com duas regras escritas para a Loja Aurora:

- sql-concatenado: uma consulta SQL montada colando um valor no texto (+, f-string, % ou .format);
- rastro-na-resposta: o rastro do Python (traceback) indo para a resposta do cliente.

Como no Semgrep, um comentário "# nosemgrep: nome-da-regra" na linha do achado, ou na linha
de cima, faz a regra ignorar aquele trecho. O achado continua aparecendo, marcado como ignorado,
para alguém conferir o motivo. Sai com 1 quando sobra algum achado não ignorado.

Uma regra olha o formato do código, não o que ele quer dizer. Ela não sabe qual é a regra de
negócio da loja nem quem pode abrir cada rota.
"""
import ast
import re
import sys
from pathlib import Path

SQL = re.compile(r'\b(select|insert|update|delete)\b|\bwhere\b|\border\s+by\b', re.I)
REGRAS = {
    'sql-concatenado': 'consulta SQL montada colando um valor no texto (CWE-89): valor vai por "?", coluna sai de uma lista do app',
    'rastro-na-resposta': 'o rastro do Python vai para a resposta do cliente (CWE-209): o detalhe fica no log',
}


def partes(no):
    """As partes de um texto montado: (textos fixos, quantas partes vêm de fora)."""
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
        a, b = partes(no.left), partes(no.right)
        return a[0] + b[0], a[1] + b[1]
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return [no.value], 0
    if isinstance(no, ast.JoinedStr):
        fixos = [v.value for v in no.values if isinstance(v, ast.Constant)]
        return fixos, sum(isinstance(v, ast.FormattedValue) for v in no.values)
    return [], 1


def montagens(arvore):
    """Cada texto montado do arquivo, uma vez só (a soma inteira, não cada pedaço dela)."""
    dentro = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
            dentro.update((id(no.left), id(no.right)))
    for no in ast.walk(arvore):
        if id(no) in dentro:
            continue
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add) or isinstance(no, ast.JoinedStr):
            fixos, de_fora = partes(no)
            yield no, fixos, de_fora
        elif isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mod) \
                and isinstance(no.left, ast.Constant) and isinstance(no.left.value, str):
            yield no, [no.left.value], 1
        elif isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr == 'format' \
                and isinstance(no.func.value, ast.Constant) and isinstance(no.func.value.value, str):
            yield no, [no.func.value.value], len(no.args) + len(no.keywords)


def nome_da_chamada(no):
    f = no.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else '')


def ignorado(linhas, numero, regra):
    for n in (numero, numero - 1):
        if 1 <= n <= len(linhas):
            m = re.search(r'#\s*nosemgrep\b(?::\s*([\w\-, ]+))?', linhas[n - 1])
            if m and (not m.group(1) or regra in [r.strip() for r in m.group(1).split(',')]):
                return True
    return False


def analisar_arquivo(caminho, relativo):
    texto = Path(caminho).read_text(encoding='utf-8')
    arvore = ast.parse(texto)
    linhas = texto.splitlines()
    onde = {}
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for filho in ast.walk(no):
                if hasattr(filho, 'lineno'):
                    onde[filho.lineno] = no.name   # a função mais de dentro fica por último
    achados = []
    for no, fixos, de_fora in montagens(arvore):
        if de_fora and any(SQL.search(f) for f in fixos):
            achados.append(('sql-concatenado', no.lineno))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and nome_da_chamada(no) == 'responder':
            for filho in ast.walk(no):
                if isinstance(filho, ast.Call) and nome_da_chamada(filho) in ('format_exc', 'format_exception'):
                    achados.append(('rastro-na-resposta', no.lineno))
                    break
    return [{'regra': regra, 'arquivo': relativo, 'linha': linha, 'funcao': onde.get(linha, '(fora de função)'),
             'mensagem': REGRAS[regra], 'ignorado': ignorado(linhas, linha, regra)}
            for regra, linha in sorted(set(achados), key=lambda a: (a[1], a[0]))]


def analisar(pasta):
    pasta = Path(pasta)
    achados = []
    for arquivo in sorted(pasta.rglob('*.py')):
        partes_do_caminho = arquivo.relative_to(pasta).parts
        if '.git' in partes_do_caminho or '__pycache__' in partes_do_caminho:
            continue
        achados += analisar_arquivo(arquivo, arquivo.relative_to(pasta).as_posix())
    return achados


def linha_do_achado(a):
    marca = 'ignorado' if a['ignorado'] else 'ACHADO  '
    return f"{marca}  {a['regra']:18}  {a['arquivo']}:{a['linha']}  {a['funcao']}: {a['mensagem']}"


def main():
    pasta = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    achados = analisar(pasta)
    for a in achados:
        print(linha_do_achado(a))
    abertos = sum(not a['ignorado'] for a in achados)
    print(f'{abertos} achado(s), {len(achados) - abertos} ignorado(s) por comentário nosemgrep.')
    return 1 if abertos else 0


if __name__ == '__main__':
    sys.exit(main())
