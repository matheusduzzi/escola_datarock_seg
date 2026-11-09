"""Resume as tentativas de pagamento do checkout da Loja Aurora.

    python3 resumir_checkout.py checkout-sexta.csv
    python3 resumir_checkout.py checkout-sexta.csv --por ip
    python3 resumir_checkout.py checkout-sexta.csv --onde sessao=s-k9f2 --linhas

--por COLUNA     agrupa pela coluna (padrão: sessao)
--onde COL=VAL   usa só as linhas com esse valor; pode repetir
--linhas         mostra as linhas, em vez do resumo
--todos          mostra todos os grupos, não só os 8 com mais tentativas

Sai com 0 quando lê o arquivo e com 2 quando não consegue (caminho errado, arquivo vazio,
coluna que falta, valor ou resultado que não dá para ler). Não decide nada sozinho:
quem lê o resumo diz se é teste de cartão.
"""
import csv
import sys
from collections import OrderedDict

CAMPOS = ['hora', 'sessao', 'ip', 'email', 'produto', 'valor', 'cartao', 'resultado', 'motivo']
RESULTADOS = {'aprovado', 'recusado'}
MOSTRAR = 8


def erro(msg):
    print('Erro: ' + msg, file=sys.stderr)
    sys.exit(2)


def centavos(texto, n):
    partes = texto.split(',')
    if len(partes) != 2 or not partes[0].isdigit() or not (partes[1].isdigit() and len(partes[1]) == 2):
        erro(f'linha {n}: valor "{texto}" não está no formato 24,90')
    return int(partes[0]) * 100 + int(partes[1])


def reais(c):
    inteiro = f'{c // 100:,}'.replace(',', '.')
    return f'R$ {inteiro},{c % 100:02d}'


def ler_argumentos(args):
    if not args or args[0].startswith('--'):
        erro('diga o arquivo. Exemplo: python3 resumir_checkout.py checkout-sexta.csv')
    arquivo, por, onde, linhas, todos = args[0], 'sessao', [], False, False
    i = 1
    while i < len(args):
        a = args[i]
        if a in ('--por', '--onde'):
            if i + 1 >= len(args):
                erro(f'{a} precisa de um valor')
            if a == '--por':
                por = args[i + 1]
            else:
                if '=' not in args[i + 1]:
                    erro(f'--onde espera COLUNA=VALOR, veio "{args[i + 1]}"')
                onde.append(tuple(args[i + 1].split('=', 1)))
            i += 2
        elif a == '--linhas':
            linhas, i = True, i + 1
        elif a == '--todos':
            todos, i = True, i + 1
        else:
            erro(f'opção que não existe: {a}')
    for coluna in [por] + [c for c, _ in onde]:
        if coluna not in CAMPOS:
            erro(f'a coluna "{coluna}" não existe. As colunas são: {", ".join(CAMPOS)}')
    return arquivo, por, onde, linhas, todos


def ler(arquivo):
    try:
        with open(arquivo, encoding='utf-8-sig', newline='') as f:
            texto = f.read()
    except FileNotFoundError:
        erro(f'não achei o arquivo {arquivo}')
    except (IsADirectoryError, UnicodeDecodeError) as e:
        erro(f'não consegui ler {arquivo} ({e.__class__.__name__})')
    if not texto.strip():
        erro(f'o arquivo {arquivo} está vazio')
    leitor = csv.DictReader(texto.splitlines(), delimiter=';')
    faltam = [c for c in CAMPOS if c not in (leitor.fieldnames or [])]
    if faltam:
        erro(f'faltam colunas no cabeçalho: {", ".join(faltam)}. O separador é ponto e vírgula.')
    tentativas = []
    for n, linha in enumerate(leitor, start=2):
        if None in linha or any(linha[c] is None for c in CAMPOS):
            erro(f'linha {n}: número de colunas diferente do cabeçalho')
        if linha['resultado'] not in RESULTADOS:
            erro(f'linha {n}: resultado "{linha["resultado"]}" não é aprovado nem recusado')
        for c in ('hora', 'sessao', 'cartao'):
            if not linha[c].strip():
                erro(f'linha {n}: {c} vazio')
        linha['centavos'] = centavos(linha['valor'], n)
        tentativas.append(linha)
    if not tentativas:
        erro(f'o arquivo {arquivo} só tem o cabeçalho')
    return tentativas


def main():
    arquivo, por, onde, mostrar_linhas, todos = ler_argumentos(sys.argv[1:])
    tentativas = ler(arquivo)
    for coluna, valor in onde:
        tentativas = [t for t in tentativas if t[coluna] == valor]
    aprovadas = sum(t['resultado'] == 'aprovado' for t in tentativas)
    filtro = ''.join(f' ({c} = {v})' for c, v in onde)
    print(f'{arquivo}{filtro}: {len(tentativas)} tentativa(s), {aprovadas} aprovada(s), {len(tentativas) - aprovadas} recusada(s)')
    if not tentativas:
        return
    if mostrar_linhas:
        for t in tentativas:
            motivo = f' ({t["motivo"]})' if t['motivo'] else ''
            print(f'  {t["hora"]}  {t["sessao"]}  {t["ip"]}  {t["email"]}  {t["produto"]}  {reais(t["centavos"])}  {t["cartao"]}  {t["resultado"]}{motivo}')
        return
    grupos = OrderedDict()
    for t in tentativas:
        grupos.setdefault(t[por], []).append(t)
    ordem = sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[1][0]['hora']))
    print(f'Por {por}: {len(grupos)} grupo(s)')
    print(f'  {por:<26} tentativas  cartões  recusas  aprovadas  valores                  das       às')
    for chave, ts in (ordem if todos else ordem[:MOSTRAR]):
        valores = sorted(t['centavos'] for t in ts)
        faixa = reais(valores[0]) if valores[0] == valores[-1] else f'{reais(valores[0])} a {reais(valores[-1])}'
        recusas = sum(t['resultado'] == 'recusado' for t in ts)
        horas = sorted(t['hora'] for t in ts)
        nome = chave[:26] if chave else '(vazio)'
        print(f'  {nome:<26} {len(ts):>10}  {len({t["cartao"] for t in ts}):>7}  {recusas:>7}  {len(ts) - recusas:>9}  {faixa:<23}  {horas[0]}  {horas[-1]}')
    if not todos and len(ordem) > MOSTRAR:
        resto = ordem[MOSTRAR:]
        print(f'  ... e mais {len(resto)} grupo(s), com {max(len(ts) for _, ts in resto)} tentativa(s) ou menos cada (--todos mostra)')


if __name__ == '__main__':
    main()
