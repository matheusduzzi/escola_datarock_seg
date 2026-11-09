"""Porteiro: fica entre o agente e as ferramentas e aplica o contrato de acesso.

O agente pede, o porteiro decide. O modelo não participa da decisão.

    python3 porteiro.py checar CONTRATO.csv               # o contrato tem problema?
    python3 porteiro.py rodar CONTRATO.csv PEDIDOS.jsonl  # passa os pedidos do agente pelo contrato
    python3 porteiro.py confirmar N "FRASE"               # uma pessoa confirma o pedido que está esperando
    python3 porteiro.py ver                               # o que mudou no banco da loja
    python3 porteiro.py zerar                             # volta o banco, a fila e o registro ao começo

Códigos de saída: 0 deu certo; 1 o contrato tem problema ou a confirmação foi recusada;
2 o comando ou o arquivo não pode ser lido.

Tudo fica na pasta em que você roda: loja.db (o banco da loja), pendentes.json (o que espera
uma pessoa e o número do último pedido) e registro.csv (cada decisão do porteiro, uma por linha).
"""
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path

PASTA = Path.cwd()
AQUI = Path(__file__).resolve().parent
BANCO = PASTA / 'loja.db'
PENDENTES = PASTA / 'pendentes.json'
REGISTRO = PASTA / 'registro.csv'
FERRAMENTAS = AQUI / 'ferramentas.csv'

CABECALHO = ['ferramenta', 'tipo', 'coluna', 'confirmacao']
COLUNAS = {'sozinho': 'faz sozinho', 'confirma': 'pede confirmação', 'nunca': 'nunca faz'}
TIPOS = {
    'leitura': 'só lê',
    'escrita': 'muda alguma coisa e dá para desfazer',
    'destrutiva': 'apaga ou desfaz algo que não volta fácil',
    'pagamento': 'paga',
    'estorno': 'devolve dinheiro',
    'exclusao': 'apaga dado de cliente ou conversa',
    'credencial': 'lê ou mostra senha, chave ou token',
    'terceiro': 'manda dado para fora da loja',
    'pacote': 'instala ou atualiza pacote',
    'teste': 'mexe em teste',
    'publica': 'publica ou leva para produção',
}
# Os cinco que nunca ficam em "faz sozinho". Se a tarefa pede um deles, ele pede confirmação digitada.
OS_CINCO = ('pagamento', 'estorno', 'exclusao', 'credencial', 'terceiro')
PEDEM_DIGITADA = OS_CINCO + ('destrutiva', 'pacote')
CONFIRMACOES = ('sim', 'digitada')

PEDIDOS_INICIAIS = [
    # id, cliente, produto, quantidade, preço unitário em centavos, status, endereço
    (1, 'Bia Santos', 'Luminária de mesa Aurora', 1, 24990, 'pago', 'Rua das Acácias, 120'),
    (2, 'Bia Santos', 'Vela aromática Alecrim', 2, 6990, 'aguardando pagamento', 'Rua das Acácias, 120'),
    (3, 'Caio Lima', 'Luminária de piso Arco', 1, 58900, 'pago', 'Av. Brasil, 1500, ap. 32'),
    (4, 'Duda Rocha', 'Manta de algodão Serra', 1, 15990, 'aguardando pagamento', 'Rua Ipê, 45'),
]
CLIENTES_INICIAIS = [
    ('Bia Santos', 'bia@cliente.example', '(19) 90000-0101'),
    ('Caio Lima', 'caio@cliente.example', '(19) 90000-0102'),
    ('Duda Rocha', 'duda@cliente.example', '(19) 90000-0103'),
]


class Erro(Exception):
    """Arquivo ou comando que não dá para ler: sai com código 2."""


def reais(centavos):
    inteiro, resto = divmod(int(round(centavos)), 100)
    return 'R$ ' + f'{inteiro:,}'.replace(',', '.') + f',{resto:02d}'


def ler_csv(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        raise Erro(f'arquivo não encontrado: {caminho.name}')
    texto = caminho.read_text(encoding='utf-8-sig')
    if not texto.strip():
        raise Erro(f'{caminho.name}: o arquivo está vazio')
    return list(csv.reader(io.StringIO(texto)))


def catalogo():
    linhas = ler_csv(FERRAMENTAS)
    cab = [c.strip() for c in linhas[0]]
    itens = {}
    for linha in linhas[1:]:
        if not any(c.strip() for c in linha):
            continue
        d = dict(zip(cab, (c.strip() for c in linha)))
        itens[d['ferramenta']] = d
    return itens


def ler_contrato(caminho):
    """Lê o contrato: uma lista de dicts, cada um com o número da linha no arquivo."""
    linhas = ler_csv(caminho)
    cab = [c.strip() for c in linhas[0]]
    if cab != CABECALHO:
        raise Erro(f'{Path(caminho).name}: o cabeçalho precisa ser {",".join(CABECALHO)}')
    itens = []
    for n, linha in enumerate(linhas[1:], start=2):
        if not any(c.strip() for c in linha):
            continue
        if len(linha) != len(CABECALHO):
            raise Erro(f'{Path(caminho).name}, linha {n}: {len(linha)} campos, esperava {len(CABECALHO)}')
        d = dict(zip(CABECALHO, (c.strip() for c in linha)))
        d['linha'] = n
        itens.append(d)
    if not itens:
        raise Erro(f'{Path(caminho).name}: o contrato não tem nenhuma ferramenta')
    return itens


def checar_itens(itens):
    cat = catalogo()
    problemas = []
    vistos = {}
    agentes = {cat[i['ferramenta']]['agente'] for i in itens if i['ferramenta'] in cat}
    for i in itens:
        nome, n = i['ferramenta'], i['linha']
        onde = f'linha {n}, {nome or "(sem nome)"}'
        if not nome:
            problemas.append(f'linha {n}: a ferramenta está vazia')
            continue
        if nome in vistos:
            problemas.append(f'{onde}: a ferramenta já aparece na linha {vistos[nome]}; cada uma fica numa coluna só')
            continue
        vistos[nome] = n
        if agentes and nome not in cat:
            problemas.append(f'{onde}: essa ferramenta não existe no ferramentas.csv do kit; veja o nome')
            continue
        tipo, coluna, conf = i['tipo'], i['coluna'], i['confirmacao']
        if tipo not in TIPOS:
            problemas.append(f'{onde}: tipo «{tipo}» não existe; use um de: {", ".join(TIPOS)}')
            continue
        if nome in cat and cat[nome]['tipo'] != tipo:
            problemas.append(f'{onde}: no kit, essa ferramenta é do tipo «{cat[nome]["tipo"]}», não «{tipo}»; '
                             'o tipo diz o que ela faz, não o que você gostaria que ela fizesse')
            continue
        if coluna not in COLUNAS:
            problemas.append(f'{onde}: coluna «{coluna}» não existe; use sozinho, confirma ou nunca')
            continue
        if coluna == 'sozinho' and tipo in OS_CINCO:
            problemas.append(f'{onde}: {TIPOS[tipo]} e está em «faz sozinho»; pagamento, estorno, exclusão, '
                             'credencial e envio a terceiro nunca ficam nessa coluna')
        elif coluna == 'sozinho' and tipo == 'destrutiva':
            problemas.append(f'{onde}: {TIPOS[tipo]} e está em «faz sozinho»; ação destrutiva pede confirmação digitada')
        elif coluna == 'sozinho' and tipo == 'pacote':
            problemas.append(f'{onde}: instalar pacote pede confirmação, com o nome e o mantenedor na tela')
        elif coluna == 'sozinho' and tipo == 'teste':
            problemas.append(f'{onde}: mexer em teste pede confirmação; apagar ou pular teste para fazer passar fica em «nunca faz»')
        elif coluna == 'sozinho' and tipo == 'publica':
            problemas.append(f'{onde}: {TIPOS[tipo]} e está em «faz sozinho»; quem leva para produção é uma pessoa')
        if coluna == 'confirma':
            if conf not in CONFIRMACOES:
                problemas.append(f'{onde}: diga como a pessoa confirma: sim ou digitada')
            elif conf == 'sim' and tipo in PEDEM_DIGITADA:
                problemas.append(f'{onde}: {TIPOS[tipo]} e a confirmação é «sim»; aqui a pessoa digita a frase que o porteiro mostra')
    for agente in sorted(agentes):
        faltam = [f for f, d in cat.items() if d['agente'] == agente and f not in vistos]
        for f in faltam:
            problemas.append(f'{f}: o agente {agente} tem essa ferramenta e ela não está no contrato; decida a coluna')
    return problemas, agentes


def contar(itens):
    por = {c: [i['ferramenta'] for i in itens if i['coluna'] == c] for c in COLUNAS}
    return '; '.join(f'{COLUNAS[c]}: {len(por[c])}' for c in COLUNAS)


def cmd_checar(caminho):
    itens = ler_contrato(caminho)
    problemas, agentes = checar_itens(itens)
    nome = Path(caminho).name
    print(f'{nome}: {len(itens)} ferramenta(s); {contar(itens)}')
    if not agentes:
        print('Ferramentas suas, fora do kit: o porteiro usa o tipo que você escreveu.')
    if problemas:
        print('\nProblemas:')
        for p in problemas:
            print('  - ' + p)
        print(f'\nResumo: {len(problemas)} problema(s).')
        return 1
    print('\nResumo: nenhum problema.')
    return 0


# ---------- banco da loja ----------

def montar_banco():
    if BANCO.exists():
        BANCO.unlink()
    con = sqlite3.connect(BANCO)
    con.executescript('''
        create table clientes (nome text primary key, email text, telefone text);
        create table pedidos (id integer primary key, cliente text, produto text, quantidade integer,
                              preco_centavos integer, status text, endereco text);
        create table estornos (pedido integer, valor_centavos integer);
        create table pagamentos (alvo text, valor_centavos integer);
        create table enviados (destino text, para text, texto text);
        create table feito (n integer, ferramenta text, alvo text, detalhe text);
    ''')
    con.executemany('insert into clientes values (?, ?, ?)', CLIENTES_INICIAIS)
    con.executemany('insert into pedidos values (?, ?, ?, ?, ?, ?, ?)', PEDIDOS_INICIAIS)
    con.commit()
    return con


def banco():
    if not BANCO.exists():
        return montar_banco()
    return sqlite3.connect(BANCO)


def numero_do_pedido(alvo):
    partes = alvo.lower().replace('nº', ' ').split()
    for p in partes:
        if p.isdigit():
            return int(p)
    raise ValueError(f'não achei o número do pedido em «{alvo}»')


def executar(con, n, p):
    """Faz o efeito da ferramenta no banco da loja. Só roda depois que o porteiro deixou."""
    f, alvo, det = p['ferramenta'], p.get('alvo', ''), p.get('detalhe', '')
    if f == 'responder_cliente':
        con.execute('insert into enviados values (?, ?, ?)', (alvo, 'cliente', det))
    elif f == 'enviar_para_terceiro':
        con.execute('insert into enviados values (?, ?, ?)', (alvo, 'fora da loja', det))
    elif f == 'mudar_endereco':
        con.execute('update pedidos set endereco = ? where id = ?', (det, numero_do_pedido(alvo)))
    elif f == 'cancelar_item':
        con.execute('update pedidos set quantidade = quantidade - 1 where id = ? and quantidade > 0', (numero_do_pedido(alvo),))
    elif f == 'estornar':
        con.execute('insert into estornos values (?, ?)', (numero_do_pedido(alvo), int(round(float(p.get('valor', 0)) * 100))))
    elif f == 'pagar_etiqueta':
        con.execute('insert into pagamentos values (?, ?)', (alvo, int(round(float(p.get('valor', 0)) * 100))))
    elif f == 'apagar_cliente':
        con.execute('delete from clientes where nome = ?', (alvo,))
    con.execute('insert into feito values (?, ?, ?, ?)', (n, f, alvo, det))
    con.commit()


def descrever(p):
    txt = p['ferramenta']
    if p.get('alvo'):
        txt += ' ' + p['alvo']
    if p.get('valor') not in (None, ''):
        txt += ', ' + reais(float(p['valor']) * 100)
    if p.get('veio_de'):
        txt += f' ({p["veio_de"]})'
    return txt


def anotar(linha):
    novo = not REGISTRO.exists()
    with open(REGISTRO, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if novo:
            w.writerow(['n', 'ferramenta', 'alvo', 'veio_de', 'decisao', 'motivo'])
        w.writerow(linha)


def ler_pendentes():
    if not PENDENTES.exists():
        return {'ultimo_pedido': 0, 'proximo': 1, 'fila': {}}
    return json.loads(PENDENTES.read_text(encoding='utf-8'))


def gravar_pendentes(d):
    PENDENTES.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def frase_de(p, verbo):
    return f'{verbo} {p.get("alvo", "")}'.strip()


def cmd_rodar(contrato, arq_pedidos):
    itens = ler_contrato(contrato)
    problemas, _ = checar_itens(itens)
    if problemas:
        print(f'{Path(contrato).name} tem {len(problemas)} problema(s). O porteiro não abre com contrato com problema.')
        print(f'Rode: python3 porteiro.py checar {Path(contrato).name}')
        return 1
    caminho = Path(arq_pedidos)
    if not caminho.is_file():
        raise Erro(f'arquivo não encontrado: {caminho.name}')
    regra = {i['ferramenta']: i for i in itens}
    cat = catalogo()
    con = banco()
    fila = ler_pendentes()
    n = fila.get('ultimo_pedido', 0)
    contagem = {'FEITO': 0, 'AGUARDA': 0, 'RECUSADO': 0}
    print(f'Contrato: {Path(contrato).name} ({contar(itens)})\n')
    for bruto in caminho.read_text(encoding='utf-8-sig').splitlines():
        if not bruto.strip():
            continue
        n += 1
        try:
            p = json.loads(bruto)
            if not isinstance(p, dict) or not p.get('ferramenta'):
                raise ValueError
        except ValueError:
            print(f'{n}. pedido que não dá para ler: RECUSADO, o porteiro só aceita pedido com ferramenta')
            anotar([n, '', '', '', 'RECUSADO', 'pedido ilegível'])
            contagem['RECUSADO'] += 1
            continue
        f = p['ferramenta']
        r = regra.get(f)
        if r is None:
            decisao, motivo = 'RECUSADO', f'{f} não está no contrato; o que não está no contrato, o porteiro recusa'
        elif r['coluna'] == 'nunca':
            decisao, motivo = 'RECUSADO', f'{f} está em «nunca faz»'
        elif r['coluna'] == 'sozinho':
            try:
                executar(con, n, p)
                decisao, motivo = 'FEITO', ''
            except (ValueError, sqlite3.Error) as e:
                decisao, motivo = 'RECUSADO', f'a ferramenta não rodou: {e}'
        else:
            k = fila['proximo']
            fila['proximo'] += 1
            verbo = cat.get(f, {}).get('verbo') or f.upper()
            frase = frase_de(p, verbo) if r['confirmacao'] == 'digitada' else 'sim'
            fila['fila'][str(k)] = {'n': n, 'pedido': p, 'frase': frase}
            decisao = 'AGUARDA'
            if r['confirmacao'] == 'digitada':
                motivo = f'confirmação nº {k}; a pessoa digita: {frase}'
            else:
                motivo = f'confirmação nº {k}; a pessoa responde: sim'
        texto = f'{n}. {descrever(p)}: '
        texto += {'FEITO': 'FEITO', 'AGUARDA': 'AGUARDA CONFIRMAÇÃO', 'RECUSADO': 'RECUSADO'}[decisao]
        if motivo:
            texto += ', ' + motivo
        print(texto)
        if decisao == 'AGUARDA' and f == 'instalar_pacote':
            print(f'   pacote {p.get("alvo", "?")}, versão {p.get("versao", "?")}, mantenedor {p.get("mantenedor", "?")}: '
                  'olhe o pacote no npm antes de confirmar')
        if p.get('confirmacao') and decisao == 'AGUARDA':
            print('   o pedido trazia uma confirmação pronta; ela não vale: quem confirma é uma pessoa, pelo comando confirmar')
        anotar([n, f, p.get('alvo', ''), p.get('veio_de', ''), decisao, motivo])
        contagem[decisao] += 1
    fila['ultimo_pedido'] = n
    gravar_pendentes(fila)
    con.close()
    print(f'\nResumo: {contagem["FEITO"]} feito(s), {contagem["AGUARDA"]} aguardando confirmação, {contagem["RECUSADO"]} recusado(s).')
    if contagem['AGUARDA']:
        print('Para confirmar: python3 porteiro.py confirmar N "FRASE"')
    return 0


def cmd_confirmar(k, frase):
    fila = ler_pendentes()
    item = fila['fila'].get(str(k))
    if item is None:
        print(f'Não existe confirmação nº {k} esperando. Rode python3 porteiro.py ver para ver a fila.')
        return 1
    p = item['pedido']
    if frase.strip() != item['frase']:
        print(f'RECUSADO: a frase não confere. Para {descrever(p)}, a pessoa digita: {item["frase"]}')
        print('Nada foi feito. O pedido continua esperando.')
        anotar([item['n'], p['ferramenta'], p.get('alvo', ''), p.get('veio_de', ''), 'RECUSADO', f'confirmação nº {k} com frase errada'])
        return 1
    con = banco()
    try:
        executar(con, item['n'], p)
    except (ValueError, sqlite3.Error) as e:
        print(f'A ferramenta não rodou: {e}')
        return 1
    finally:
        con.close()
    del fila['fila'][str(k)]
    gravar_pendentes(fila)
    anotar([item['n'], p['ferramenta'], p.get('alvo', ''), p.get('veio_de', ''), 'FEITO', f'confirmado pela pessoa (nº {k})'])
    print(f'FEITO: {descrever(p)}, confirmado pela pessoa.')
    return 0


def cmd_ver():
    con = banco()
    print('Pedidos:')
    for pid, cli, prod, qtd, preco, status, end in con.execute('select * from pedidos order by id'):
        print(f'  {pid}. {cli}, {qtd} × {prod}, {reais(qtd * preco)}, {status}, entrega em {end}')
    ncli = con.execute('select count(*) from clientes').fetchone()[0]
    nest, soma = con.execute('select count(*), coalesce(sum(valor_centavos), 0) from estornos').fetchone()
    npag, somap = con.execute('select count(*), coalesce(sum(valor_centavos), 0) from pagamentos').fetchone()
    para_cli = con.execute("select count(*) from enviados where para = 'cliente'").fetchone()[0]
    para_fora = con.execute("select count(*) from enviados where para = 'fora da loja'").fetchone()[0]
    print(f'Clientes no cadastro: {ncli}')
    print(f'Estornos: {nest}, total {reais(soma)}')
    print(f'Pagamentos: {npag}, total {reais(somap)}')
    print(f'Mensagens enviadas: {para_cli} para cliente, {para_fora} para fora da loja')
    fila = ler_pendentes()['fila']
    if fila:
        print('Esperando confirmação:')
        for k, item in fila.items():
            print(f'  nº {k}: {descrever(item["pedido"])}; a pessoa digita: {item["frase"]}')
    else:
        print('Esperando confirmação: nada')
    con.close()
    return 0


def cmd_zerar():
    con = montar_banco()
    con.close()
    for arq in (PENDENTES, REGISTRO):
        if arq.exists():
            arq.unlink()
    print('Banco, fila de confirmação e registro voltaram ao começo.')
    return 0


USO = ('uso: python3 porteiro.py checar CONTRATO.csv | rodar CONTRATO.csv PEDIDOS.jsonl | '
       'confirmar N "FRASE" | ver | zerar')


def main(args):
    try:
        if len(args) == 2 and args[0] == 'checar':
            return cmd_checar(args[1])
        if len(args) == 3 and args[0] == 'rodar':
            return cmd_rodar(args[1], args[2])
        if len(args) == 3 and args[0] == 'confirmar':
            if not args[1].isdigit():
                raise Erro('o número da confirmação precisa ser um número, como 1')
            return cmd_confirmar(int(args[1]), args[2])
        if args == ['ver']:
            return cmd_ver()
        if args == ['zerar']:
            return cmd_zerar()
        raise Erro(USO)
    except Erro as e:
        print(e if str(e).startswith('uso:') else f'erro: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
